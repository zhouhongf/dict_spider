import asyncio

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

from functools import wraps


# 使用函数装饰器singleton实现单列
def singleton(cls):
    """
    A singleton created by using decorator
    :param cls: cls
    :return: instance
    """
    _instances = {}

    # 装饰器 作用于类 cls
    # 使用不可变的类地址作为键，其实例作为值，
    # 每次创造实例时，首先查看该类是否存在实例，存在的话直接返回该实例即可，
    # 否则新建一个实例并存放在字典中。
    @wraps(cls)
    def instance(*args, **kw):
        if cls not in _instances:
            _instances[cls] = cls(*args, **kw)
        return _instances[cls]

    return instance



