#!/usr/bin/env python
# Request类中，通过构造方法实例化后，添加了form_data的实例属性, 用来实现Spider的POST请求
import asyncio
import weakref
import aiohttp
import async_timeout
from inspect import iscoroutinefunction
from types import AsyncGeneratorType
from typing import Coroutine, Optional, Tuple
from asyncio.locks import Semaphore

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

from .exceptions import InvalidRequestMethod
from .response import Response
from config import Logger
from .tools import get_random_user_agent


class Request(object):
    """
    Request class for each request
    Request的主要作用是方便地处理网络请求，最终返回一个Response对象。
    主要提供的方法有：
    Request().fetch：请求一个网页资源，可以单独使用
    Request().fetch_callback：为Spider类提供的和核心方法
    """

    name = "Request"

    # Default config
    REQUEST_CONFIG = {
        "RETRIES": 3,
        "DELAY": 0,
        "RETRY_DELAY": 0,
        "TIMEOUT": 10,
        "RETRY_FUNC": Coroutine,
        "VALID": Coroutine,
    }

    METHOD = ["GET", "POST"]

    def __init__(
        self,
        url: str,
        method: str = "GET",
        *,
        callback=None,
        encoding: Optional[str] = None,
        headers: dict = None,
        metadata: dict = None,
        request_config: dict = None,
        request_session=None,
        form_data: dict = None,
        **aiohttp_kwargs,
    ):
        """
        Initialization parameters
        :param url: Target url
        :param method: HTTP method
        :param callback: Callback func
        :param encoding: Html encoding
        :param headers: Request headers
        :param metadata: Send the audit to callback func
        :param request_config: Manage the target request
        :param request_session: aiohttp.ClientSession
        :param aiohttp_kwargs:
        """
        self.url = url
        self.method = method.upper()

        if self.method not in self.METHOD:
            raise InvalidRequestMethod(f"{self.method} method is not supported")

        self.callback = callback
        self.encoding = encoding
        self.headers = headers or {}
        self.metadata = metadata or {}
        self.request_config = (
            self.REQUEST_CONFIG if request_config is None else request_config
        )
        self.request_session = request_session
        # 自己增加的属性，用于传递POST请求的form_data参数
        self.form_data = form_data

        self.ssl = aiohttp_kwargs.pop("ssl", False)
        self.aiohttp_kwargs = aiohttp_kwargs

        self.close_request_session = False
        self.logger = Logger(level='warning').logger
        self.retry_times = self.request_config.get("RETRIES", 3)

    @property
    def current_request_session(self):
        if self.request_session is None:
            self.request_session = aiohttp.ClientSession()
            self.close_request_session = True
        return self.request_session

    async def fetch(self, delay=True) -> Response:
        """Fetch all the information by using aiohttp"""
        if delay and self.request_config.get("DELAY", 0) > 0:
            await asyncio.sleep(self.request_config["DELAY"])

        timeout = self.request_config.get("TIMEOUT", 10)
        try:
            async with async_timeout.timeout(timeout):
                # 用于真正发起request请求
                resp = await self._make_request()
            try:
                resp_data = await resp.text(encoding=self.encoding)
            except UnicodeDecodeError:
                resp_data = await resp.read()

            response = Response(
                url=self.url,
                method=self.method,
                encoding=resp.get_encoding(),
                html=resp_data,
                metadata=self.metadata,
                cookies=resp.cookies,
                headers=resp.headers,
                history=resp.history,
                status=resp.status,
                aws_json=resp.json,
                aws_text=resp.text,
                aws_read=resp.read,
            )
            # Retry middleware
            aws_valid_response = self.request_config.get("VALID")
            if aws_valid_response and iscoroutinefunction(aws_valid_response):
                response = await aws_valid_response(response)
            if response.ok:
                return response
            else:
                return await self._retry(error_msg=f"Request url failed with status {response.status}!")
        except asyncio.TimeoutError:
            return await self._retry(error_msg="timeout")
        except Exception as e:
            return await self._retry(error_msg=e)
        finally:
            await self._close_request()

    async def fetch_callback(self, sem: Semaphore) -> Tuple[AsyncGeneratorType, Response]:
        """
        Request the target url and then call the callback function
        :param sem: Semaphore
        :return: Tuple[AsyncGeneratorType, Response]
        """
        try:
            async with sem:
                response = await self.fetch()
        except Exception as e:
            response = None
            self.logger.error(f"<Error: {self.url} {e}>")

        if self.callback is not None:
            if iscoroutinefunction(self.callback):
                callback_result = await self.callback(response)
            else:
                callback_result = self.callback(response)
        else:
            callback_result = None
        # response.callback_result = callback_result
        return callback_result, response

    async def _close_request(self):
        if self.close_request_session:
            await self.request_session.close()

    # ！！用于真正的发起request请求
    async def _make_request(self):
        """Make a request by using aiohttp"""
        self.logger.info(f"<{self.method}: {self.url}>")
        user_agent = await get_random_user_agent()
        self.headers.update({'User-Agent': user_agent})
        if self.method == "GET":
            request_func = self.current_request_session.get(self.url, headers=self.headers, ssl=self.ssl, **self.aiohttp_kwargs)
        else:
            request_func = self.current_request_session.post(self.url, headers=self.headers, ssl=self.ssl, data=self.form_data, **self.aiohttp_kwargs)
        resp = await request_func
        return resp

    async def _retry(self, error_msg):
        """Manage request"""
        if self.retry_times > 0:
            # Sleep to give server a chance to process/cache prior request
            if self.request_config.get("RETRY_DELAY", 0) > 0:
                await asyncio.sleep(self.request_config["RETRY_DELAY"])

            retry_times = self.request_config.get("RETRIES", 3) - self.retry_times + 1
            self.logger.error(f"<Retry url: {self.url}>, Retry times: {retry_times}, Retry message: {error_msg}>")
            self.retry_times -= 1
            retry_func = self.request_config.get("RETRY_FUNC")
            if retry_func and iscoroutinefunction(retry_func):
                request_ins = await retry_func(weakref.proxy(self))
                if isinstance(request_ins, Request):
                    return await request_ins.fetch()
            return await self.fetch()
        else:
            response = Response(
                url=self.url,
                method=self.method,
                metadata=self.metadata,
                cookies={},
                history=(),
                headers=None,
            )

            return response

    def __repr__(self):
        return f"<{self.method} {self.url}>"
