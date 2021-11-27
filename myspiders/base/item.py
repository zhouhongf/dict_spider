from inspect import isawaitable
from lxml import etree
from typing import Any, Union
import json
from .exceptions import IgnoreThisItem, InvalidFuncType
from .field import BaseField
from .request import Request
from bs4 import BeautifulSoup
from bs4.element import Tag


class ItemMeta(type):
    """
    Metaclass for an item, 最关键的是新建了一个‘__fields’的类属性
    """
    # attrs包括：'__module__'（模块名称）,  '__qualname__'（类名称）, '__doc__'（类中使用3引号的描述）,
    # '__init__'（构造方法）, '__repr__'，以及类中 所有的成员属性 和 方法。
    # '__dict__' 列出所有的实例属性。
    # attrs.items()以元组键值的格式，显示出来
    # if isinstance(object, BaseField)从attrs.items()筛选出 符合BaseField实例的 成员属性和方法 返回给__fields
    def __new__(cls, name, bases, attrs):
        __fields = dict(
            {
                (field_name, attrs.pop(field_name)) for field_name, object in list(attrs.items())
                if isinstance(object, BaseField)
            }
        )
        # __fields就是具体Item类中的属性， 父类__fields的内容为{}，
        # 子类DoubanItem的属性为{'target_item': 内容, 'title': 内容, 'cover': 内容, 'abstract': 内容}, 不包含方法
        attrs["__fields"] = __fields
        new_class = type.__new__(cls, name, bases, attrs)
        return new_class


class Item(metaclass=ItemMeta):
    """
    Item class for each item
    Item的主要作用是定义以及通过一定的规则提取源网页中的目标数据，它主要提供一下两个方法：
    （1）get_item：针对页面单目标数据进行提取
    （2) get_items：针对页面多目标数据进行提取
    get_item和get_items方法接收的参数是一致的：
     (1) html：网页源码
     (2) url：网页链接
     (3) html_etree：etree._Element对象
    """

    def __init__(self):
        self.ignore_item = False
        self.results = {}

    def __repr__(self):
        return f"<Item {self.results}>"

    @classmethod
    async def _parse_json(cls, *, jsondata: json):
        if jsondata is None:
            raise ValueError("jsondata is expected")
        item_ins = cls()

        fields_dict = getattr(item_ins, "__fields", {})
        for field_name, field_value in fields_dict.items():
            if not field_name.startswith("target_"):
                value = field_value.extract(jsondata=jsondata)

                clean_method = getattr(item_ins, f"clean_{field_name}", None)
                if clean_method is not None and callable(clean_method):
                    try:
                        aws_clean_func = clean_method(value)
                        if isawaitable(aws_clean_func):
                            value = await aws_clean_func
                        else:
                            raise InvalidFuncType(f"<Item: clean_method must be a coroutine function>")
                    except IgnoreThisItem:
                        item_ins.ignore_item = True

                setattr(item_ins, field_name, value)
                item_ins.results[field_name] = value
        return item_ins

    @classmethod
    async def get_json(cls, *, jsondata: json = "", **kwargs):
        # 从Item子类的类属性提取target_item属性
        items_field = getattr(cls, "__fields", {}).get("target_item", None)
        if items_field:
            items_field.many = True
            # 从json_data当中提取出target_item部分
            items_json = items_field.extract(jsondata=jsondata)

            if items_json:
                # 遍历target_item部分，提取子属性的值
                for each_json in items_json:
                    item = await cls._parse_json(jsondata=each_json)
                    yield item
            else:
                raise ValueError("get_json：Get target_item's value error!")
        else:
            if isinstance(jsondata, list):              # 从Item子类的类属性中不存在target_item属性，则直接提取子属性的值
                for each_json in jsondata:
                    yield await cls._parse_json(jsondata=each_json)
            else:
                yield await cls._parse_json(jsondata=jsondata)


    # 3、解析html, 根据Item子类的类属性，和类方法，开头prefix来区分，和提取要素
    # target_开头的类属性，为html上的target部分，再执行Field类中的extract()方法进行细分提取
    # clean_ + 类属性 形式的方法，进一步筛选 类属性
    @classmethod
    async def _parse_html(cls, *, html_etree: etree._Element):
        if html_etree is None:
            raise ValueError("html_etree is expected")
        item_ins = cls()

        # 根据ItemMeta类新创建的new_class, 即item_ins, 获取其“__fields”属性,
        # 例子中即DoubanItem的类属性{'target_item': 内容, 'title': 内容, 'cover': 内容, 'abstract': 内容}
        fields_dict = getattr(item_ins, "__fields", {})
        for field_name, field_value in fields_dict.items():                       # 分别提取DoubanItem的类属性的名称name和值value
            if not field_name.startswith("target_"):                              # 如果属性，不是以target_开头的
                clean_method = getattr(item_ins, f"clean_{field_name}", None)     # 如果方法，是以clean_开头的
                value = field_value.extract(html_etree)                           # 则执行Field类中的extract()方法, 返回cssselect()或xpath()方法解析后的内容

                if clean_method is not None and callable(clean_method):
                    try:
                        aws_clean_func = clean_method(value)
                        if isawaitable(aws_clean_func):                           # 如果是isawaitable()的，则执行await
                            value = await aws_clean_func
                        else:
                            raise InvalidFuncType(f"_parse_html<Item: clean_method must be a coroutine function>")
                    except IgnoreThisItem:
                        item_ins.ignore_item = True

                setattr(item_ins, field_name, value)                              # 重新设置该item_ins的field_name所对应的值value
                item_ins.results[field_name] = value                              # 设置Item的成员属性results={}的值
        return item_ins

    # 2、如果是html，则直接返回etree.HTML(html)
    # 如果是url, 则通过request获取html后，再返回etree.HTML(html)
    @classmethod
    async def _get_html(cls, html: str = "", url: str = "", **kwargs):
        if html or url:
            if url:
                sem = kwargs.pop("sem", None)
                request = Request(url, **kwargs)
                if sem:
                    _, response = await request.fetch_callback(sem=sem)
                else:
                    response = await request.fetch()
                html = response.html
            return etree.HTML(html)
        else:
            ValueError("_get_html(url or html_etree) is expected")

    @classmethod
    async def get_item(cls, *, html: str = "", url: str = "", html_etree: etree._Element = None, **kwargs) -> Any:
        if html_etree is None:
            html_etree = await cls._get_html(html, url, **kwargs)

        return await cls._parse_html(html_etree=html_etree)

    # 1、从spider子类实例中执行DoubanItem.get_items(html=response.html)，来到Item类中
    @classmethod
    async def get_items(cls, *, html: str = "", url: str = "", html_etree: etree._Element = None, **kwargs):
        if html_etree is None:
            html_etree = await cls._get_html(html, url, **kwargs)

        # 从Item子类的类属性提取target_item属性
        items_field = getattr(cls, "__fields", {}).get("target_item", None)
        if items_field:
            items_field.many = True
            # 从html_tree当中提取出target_item部分
            items_html_etree = items_field.extract(html_etree=html_etree, is_source=True)
            if items_html_etree:
                # 遍历target_item部分，提取子属性的值
                for each_html_etree in items_html_etree:
                    item = await cls._parse_html(html_etree=each_html_etree)
                    if not item.ignore_item:
                        yield item
            else:
                value_error_info = "get_items<Item: Failed to get target_item's value from"
                if url:
                    value_error_info = f"{value_error_info} url: {url}.>"
                if html:
                    value_error_info = f"{value_error_info} html.>"
                raise ValueError(value_error_info)
        else:
            raise ValueError("get_items：target_item is expected")


    @classmethod
    async def _get_soup(cls, html: str = "", url: str = "", **kwargs):
        if html or url:
            if url:
                sem = kwargs.pop("sem", None)
                request = Request(url, **kwargs)
                if sem:
                    _, response = await request.fetch_callback(sem=sem)
                else:
                    response = await request.fetch()

                html = response.html
            return BeautifulSoup(html, 'lxml')
        else:
            ValueError("_get_soup(url or html text) is expected")

    @classmethod
    async def get_bs4_item(cls, *, html: str = "", url: str = "", soup: BeautifulSoup = None, **kwargs) -> Any:
        if soup is None:
            soup = await cls._get_soup(html, url, **kwargs)
        return await cls._parse_soup(tag=soup)


    @classmethod
    async def get_bs4_items(cls, *, html: str = "", url: str = "", soup: BeautifulSoup = None, **kwargs):
        if soup is None:
            soup = await cls._get_soup(html, url, **kwargs)

        # 从Item子类的类属性提取target_item属性
        items_field = getattr(cls, "__fields", {}).get("target_item", None)
        if items_field:
            items_field.many = True
            # 从soup当中提取出target_item部分
            target_soup = items_field.extract(soup=soup, is_source=True)
            if target_soup:
                # 遍历target_item部分，提取子属性的值
                for one in target_soup:
                    item = await cls._parse_soup(tag=one)
                    if not item.ignore_item:
                        yield item
            else:
                value_error_info = "get_bs4_items<Item: Failed to get target_item's value from"
                if url:
                    value_error_info = f"{value_error_info} url: {url}.>"
                if html:
                    value_error_info = f"{value_error_info} html.>"
                raise ValueError(value_error_info)
        else:
            raise ValueError("get_bs4_items：target_item is expected")

    # 3、解析html, 根据Item子类的类属性，和类方法，开头prefix来区分，和提取要素
    # target_开头的类属性，为html上的target部分，再执行Field类中的extract()方法进行细分提取
    # clean_ + 类属性 形式的方法，进一步筛选 类属性
    @classmethod
    async def _parse_soup(cls, *, tag: Union[BeautifulSoup, Tag]):
        if tag is None:
            raise ValueError("Bs4 or Tag is expected")
        item_ins = cls()

        # 根据ItemMeta类新创建的new_class, 即item_ins, 获取其“__fields”属性,
        # 例子中即DoubanItem的类属性{'target_item': 内容, 'title': 内容, 'cover': 内容, 'abstract': 内容}
        fields_dict = getattr(item_ins, "__fields", {})
        for field_name, field_value in fields_dict.items():                       # 分别提取DoubanItem的类属性的名称name和值value
            if not field_name.startswith("target_"):                              # (1) 判断属性，不是以target_开头的
                value = field_value.extract(tag)                                  # (2) 执行Field类中的extract()方法，提取内容
                clean_method = getattr(item_ins, f"clean_{field_name}", None)     # (3) 查找clean_开头的方法，进一步清洗属性
                if clean_method is not None and callable(clean_method):
                    try:
                        aws_clean_func = clean_method(value)
                        if isawaitable(aws_clean_func):                           # 如果是isawaitable()的，则执行await
                            value = await aws_clean_func
                        else:
                            raise InvalidFuncType(f"_parse_soup<Item: clean_method must be a coroutine function>")
                    except IgnoreThisItem:
                        item_ins.ignore_item = True

                setattr(item_ins, field_name, value)                              # 重新设置该item_ins的field_name所对应的值value
                item_ins.results[field_name] = value                              # 设置Item的成员属性results={}的值
        return item_ins
