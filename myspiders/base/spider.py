import asyncio
import collections
import typing
import weakref
import time
from datetime import datetime
from functools import reduce
from inspect import isawaitable
from signal import SIGINT, SIGTERM
from types import AsyncGeneratorType
from aiohttp import ClientSession
from database import MongoDatabase
from config import Logger, Vocabulary
from .exceptions import (
    InvalidCallbackResult,
    NotImplementedParseError,
    NothingMatchedError,
)
from .item import Item
from .request import Request
from .response import Response


try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


class SpiderHook:

    callback_result_map: dict = None
    logger = Logger(level='warning').logger

    async def _run_spider_hook(self, hook_func):
        if callable(hook_func):
            try:
                aws_hook_func = hook_func(weakref.proxy(self))
                if isawaitable(aws_hook_func):
                    await aws_hook_func
            except Exception as e:
                self.logger.error(f"<Hook {hook_func.__name__}: {e}")

    async def process_failed_response(self, request, response):
        pass

    async def process_succeed_response(self, request, response):
        pass

    async def process_item(self, item):
        pass

    async def process_callback_result(self, callback_result):
        callback_result_name = type(callback_result).__name__
        process_func_name = self.callback_result_map.get(callback_result_name, "")
        process_func = getattr(self, process_func_name, None)
        if process_func is not None:
            await process_func(callback_result)
        else:
            raise InvalidCallbackResult(f"process_callback_result()方法中<Parse invalid callback result type: {callback_result_name}>")


class Spider(SpiderHook):
    name = None
    request_config = None
    # request_session = None

    headers: dict = None
    metadata: dict = None
    kwargs: dict = None

    failed_counts: int = 0
    success_counts: int = 0

    worker_numbers: int = 2
    concurrency: int = 3

    worker_tasks: list = []
    targets: list = []

    pattern_date = '20[0-9]{2}[-年/][01]?[0-9][-月/][0123]?[0-9]日?'
    pattern_chinese = r'[\u4e00-\u9fa5]'
    pattern_number = r'\d'
    pattern_letter = r'[a-zA-Z]'

    def __init__(
            self,
            name=None,
            start_urls: list = None,
            loop=None,
            is_async_start: bool = False,
            cancel_tasks: bool = True,
            **kwargs,
    ):
        if name is not None:
            self.name = name
        elif not getattr(self, 'name', None):
            raise ValueError("%s must have a name" % type(self).__name__)

        if not isinstance(self.targets, typing.Iterable):
            raise ValueError("In %s, targets must be type of list" % type(self).__name__)

        self.start_urls = start_urls or []
        if not isinstance(self.start_urls, typing.Iterable):
            raise ValueError("start_urls must be collections.Iterable")

        self.loop = loop
        asyncio.set_event_loop(self.loop)
        self.request_queue = asyncio.Queue()
        self.sem = asyncio.Semaphore(self.concurrency)

        # Init object-level properties  SpiderHook的类属性
        self.callback_result_map = self.callback_result_map or {}

        self.headers = self.headers or {}
        self.metadata = self.metadata or {}
        self.kwargs = self.kwargs or {}
        self.request_config = self.request_config or {}
        self.request_session = ClientSession()
        self.cancel_tasks = cancel_tasks
        self.is_async_start = is_async_start

        # Mongo数据库
        self.mongo = MongoDatabase()
        mongo_db = self.mongo.db()
        self.collection = mongo_db['english_dict']

    # 重要！处理异步回调函数的方法，在start_worker()方法中，启动该方法
    # 从返回结果callback_results中迭代每一个返回结果callback_result, 根据其不同的类别，套用不同的执行方法
    async def _process_async_callback(self, callback_results: AsyncGeneratorType, response: Response = None):
        try:
            async for callback_result in callback_results:
                if isinstance(callback_result, AsyncGeneratorType):
                    await self._process_async_callback(callback_result)
                elif isinstance(callback_result, Request):
                    self.request_queue.put_nowait(self.handle_request(request=callback_result))
                elif isinstance(callback_result, typing.Coroutine):
                    self.request_queue.put_nowait(self.handle_callback(aws_callback=callback_result, response=response))
                elif isinstance(callback_result, Item):
                    await self.process_item(callback_result)
                else:
                    await self.process_callback_result(callback_result=callback_result)
        except NothingMatchedError as e:
            error_info = f"<Field: {str(e).lower()}" + f", error url: {response.url}>"
            self.logger.error(error_info)
        except Exception as e:
            self.logger.error(e)

    async def _process_response(self, request: Request, response: Response):
        if response:
            if response.ok:
                self.success_counts += 1
                await self.process_succeed_response(request, response)
            else:
                self.failed_counts += 1
                await self.process_failed_response(request, response)

    async def _start(self, after_start=None, before_stop=None):
        print('【=======================================启动：%s=========================================】' % self.name)
        start_time = datetime.now()

        # Add signal 添加控制信号，不过只有在linux系统上才行
        for signal in (SIGINT, SIGTERM):
            try:
                self.loop.add_signal_handler(signal, lambda: asyncio.ensure_future(self.stop(signal)))
            except NotImplementedError:
                pass

        # Actually run crawling  真正开始爬取了。。。
        try:
            await self._run_spider_hook(after_start)
            await self.start_master()
            await self._run_spider_hook(before_stop)
        finally:
            await self.request_session.close()

            # Display logs about this crawl task 本次蜘蛛爬取工作的日志处理，成功次数，失败次数，用时多久
            end_time = datetime.now()
            print('----------- 用时：%s ------------' % (end_time - start_time))

    @classmethod
    async def async_start(
            cls,
            start_urls: list = None,
            loop=None,
            after_start=None,
            before_stop=None,
            cancel_tasks: bool = True,
            **kwargs,
    ):
        loop = loop or asyncio.get_event_loop()
        spider_ins = cls(start_urls=start_urls, loop=loop, is_async_start=True, cancel_tasks=cancel_tasks, **kwargs)
        await spider_ins._start(after_start=after_start, before_stop=before_stop)
        return spider_ins

    @classmethod
    def start(
            cls,
            start_urls: list = None,
            loop=None,
            after_start=None,
            before_stop=None,
            close_event_loop=True,
            **kwargs,
    ):
        loop = loop or asyncio.new_event_loop()
        spider_ins = cls(start_urls=start_urls, loop=loop, **kwargs)
        spider_ins.loop.run_until_complete(spider_ins._start(after_start=after_start, before_stop=before_stop))
        spider_ins.loop.run_until_complete(spider_ins.loop.shutdown_asyncgens())
        if close_event_loop:
            spider_ins.loop.close()
        return spider_ins

    async def handle_callback(self, aws_callback: typing.Coroutine, response):
        """Process coroutine callback function"""
        callback_result = None
        try:
            callback_result = await aws_callback
        except NothingMatchedError as e:
            self.logger.error(f"<Item: {str(e).lower()}>")
        except Exception as e:
            self.logger.error(f"<Callback[{aws_callback.__name__}]: {e}")

        return callback_result, response


    async def handle_request(self, request: Request) -> typing.Tuple[AsyncGeneratorType, Response]:
        callback_result, response = None, None
        try:
            callback_result, response = await request.fetch_callback(self.sem)
            await self._process_response(request=request, response=response)
        except NotImplementedParseError as e:
            self.logger.error(e)
        except NothingMatchedError as e:
            error_info = f"<Field: {str(e).lower()}" + f", error url: {request.url}>"
            self.logger.error(error_info)
        except Exception as e:
            self.logger.error(f"<Callback[{request.callback.__name__}]: {e}")

        return callback_result, response

    # 6、处理多个handle_request方法，如果form_datas值不为空，则执行POST请求
    # 用来解决asyncio出现too many file descriptors in select()问题的web请求, 防止一下子请求过多，而被封IP,
    # list中有超过500个以上的请求，则使用multiple_requests
    async def multiple_request(self, urls: list, form_datas: list = None, is_gather: bool = False, **kwargs):
        if is_gather:
            if form_datas:
                tasks = [self.handle_request(self.request(url=urls[0], form_data=one, **kwargs)) for one in form_datas]
            else:
                tasks = [self.handle_request(self.request(url=url, **kwargs)) for url in urls]

            resp_results = await asyncio.gather(*tasks, return_exceptions=True)
            for index, task_result in enumerate(resp_results):
                if not isinstance(task_result, RuntimeError) and task_result:
                    _, response = task_result
                    response.index = index
                    yield response
        else:
            if form_datas:
                for index, one in enumerate(form_datas):
                    _, response = await self.handle_request(self.request(url=urls[0], form_data=one, **kwargs))
                    response.index = index
                    yield response
            else:
                for index, one in enumerate(urls):          # 因为遍历集合方法中，存在异步 await方法，所以不能再call_back回原来的方法中去，否则会导致无限循环
                    _, response = await self.handle_request(self.request(url=one, **kwargs))
                    response.index = index
                    yield response

    async def parse(self, response):
        raise NotImplementedParseError("<!!! parse function is expected !!!>")

    # 【仅仅改写的process_start_urls方法的内容，将spider开始爬取的目标，使用target类，可以自由定制】
    async def process_start_urls(self):
        for target in self.targets:
            yield self.request(url=target.url, callback=self.parse, metadata={'target': target})

    # 【自定义启动方法】
    async def manual_start_urls(self):
        yield self.request()

    def request(
            self,
            url: str = 'http://httpbin.org/get',
            method: str = "GET",
            *,
            callback=None,
            encoding: typing.Optional[str] = None,
            headers: dict = None,
            metadata: dict = None,
            request_config: dict = None,
            request_session=None,
            form_data: dict = None,
            **kwargs,
    ):
        """Init a Request class for crawling html"""
        headers = headers or {}
        metadata = metadata or {}
        request_config = request_config or {}
        request_session = request_session or self.request_session
        form_data = form_data

        headers.update(self.headers.copy())
        request_config.update(self.request_config.copy())
        kwargs.update(self.kwargs.copy())
        # 如果存在form_data，则method为POST，否则为默认的GET
        if form_data:
            method = 'POST'
        return Request(
            url=url,
            method=method,
            callback=callback,
            encoding=encoding,
            headers=headers,
            metadata=metadata,
            request_config=request_config,
            request_session=request_session,
            form_data=form_data,
            **kwargs,
        )

    async def start_master(self):
        if self.targets:
            async for request_ins in self.process_start_urls():
                self.request_queue.put_nowait(self.handle_request(request_ins))
        else:
            async for request_ins in self.manual_start_urls():
                self.request_queue.put_nowait(self.handle_request(request_ins))

        workers = [asyncio.ensure_future(self.start_worker()) for i in range(self.worker_numbers)]
        for worker in workers:
            self.logger.info(f"Worker started: {id(worker)}")
        await self.request_queue.join()      # 阻塞至队列中所有的元素都被接收和处理完毕。当未完成计数降到零的时候， join() 阻塞被解除。

        # 运行到此处，代表request_queue队列中的任务都执行完成了，不再受到requests_queue.join()方法的阻塞了。
        # 然后执行的是关闭任务，和关闭loop的操作了。
        if not self.is_async_start:          # 如果不是is_async_start，即不是异步启动的，则等待执行stop()方法
            await self.stop(SIGINT)
        else:
            if self.cancel_tasks:            # 如果是异步启动的，在async_start()方法中，实例化Spider类时定义cancel_tasks为True, 则，取消前面的tasks, 执行当前异步启动的task
                await self._cancel_tasks()


    async def start_worker(self):
        while True:
            request_item = await self.request_queue.get()
            self.worker_tasks.append(request_item)
            if self.request_queue.empty():
                results = await asyncio.gather(*self.worker_tasks, return_exceptions=True)
                for task_result in results:
                    if not isinstance(task_result, RuntimeError) and task_result:
                        callback_results, response = task_result
                        if isinstance(callback_results, AsyncGeneratorType):
                            await self._process_async_callback(callback_results, response)
                self.worker_tasks = []
            self.request_queue.task_done()    # 每当消费协程调用 task_done() 表示这个条目item已经被回收，该条目所有工作已经完成，未完成计数就会减少。


    async def stop(self, _signal):
        self.logger.info(f"Stopping spider: {self.name}")
        await self._cancel_tasks()
        self.loop.stop()

    async def _cancel_tasks(self):
        tasks = []
        for task in asyncio.Task.all_tasks():
            if task is not asyncio.tasks.Task.current_task():
                tasks.append(task)
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


