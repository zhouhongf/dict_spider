#!/usr/bin/env python
import re
import json
from typing import Union, Pattern
from lxml import etree
from bs4 import BeautifulSoup, UnicodeDammit
from bs4.element import Tag, NavigableString

from .exceptions import NothingMatchedError


class BaseField(object):

    def __init__(self, default="", many: bool = False, next_request: bool = False, url_prefix: str = None):
        self.default = default
        self.many = many
        self.next_request = next_request
        self.url_prefix = url_prefix

    def extract(self, *args, **kwargs):
        raise NotImplementedError("extract is not implemented.")


class _Bs4Field(BaseField):

    def __init__(
            self,
            name: Union[str, list, Pattern, bool] = None,
            attrs: dict = None,
            recursive: bool = True,                             # bs4默认遍历查找tag的所有子孙节点，如果只想搜索tag的直接子节点,可以设置recursive=False
            string: Union[str, list, Pattern, bool] = None,
            css_select: str = None,
            default=None,
            many: bool = True,
            next_request: bool = False,
            url_prefix: str = None
    ):
        super(_Bs4Field, self).__init__(default=default, many=many, next_request=next_request, url_prefix=url_prefix)
        self.name = name
        self.attrs = attrs or {}
        self.recursive = recursive
        self.string = string
        self.css_select = css_select
        self.limit = 1 if many is False else None

    def extract(self, soup: Union[str, BeautifulSoup, Tag], is_source: bool = False):
        if isinstance(soup, str):
            soup = BeautifulSoup(soup, 'lxml')

        elements = self._get_elements(soup=soup)
        # 如果是target_item，则表明是一个预先提取的部分，为source, 供后续使用soup继续提取
        # 此处需要判断elements集合中的成员，是Tag类型还是NavigableString类型，因为只有Tag类型，才支持soup继续查找；
        # NavigableString 对象支持 遍历文档树 和 搜索文档树 中定义的大部分属性, 但并非全部。
        # 尤其是,一个字符串不能包含其它内容(tag能够包含字符串或是其它tag), 字符串不支持.contents 或 .string 属性或 find() 方法。
        if is_source:
            if elements and type(elements[0]) == Tag:
                return elements
            else:
                raise NothingMatchedError(f"BeautifulSoup is_source but No Tag found")

        if elements:
            if type(elements[0]) == Tag:
                results = [self._parse_element(one) for one in elements]
            elif type(elements[0]) == NavigableString:
                results = [self._unicode_value(one) for one in elements]
            else:
                raise NothingMatchedError(f"BeautifulSoup parsed result type is neither Tag nor NavigableString")
        elif self.default:
            results = self.default if type(self.default) == list else [self.default]
        else:
            raise NothingMatchedError(f"BeautifulSoup find Nothing, name:%s, attrs:%s, string:%s, css_select:%s" % (self.name, self.attrs, self.string, self.css_select))
        return results if not self.limit else results[0]

    def _unicode_value(self, string: NavigableString):
        value = UnicodeDammit.detwingle(string)
        return UnicodeDammit(value).unicode_markup

    def _get_elements(self, *, soup: Union[BeautifulSoup, Tag]):
        if not self.css_select:
            elements = soup.find_all(name=self.name, attrs=self.attrs, recursive=self.recursive, text=self.string, limit=self.limit)
        else:
            elements = soup.select(selector=self.css_select, limit=self.limit)
        return elements

    def _parse_element(self, element):
        raise NotImplementedError


class Bs4HtmlField(_Bs4Field):
    def _parse_element(self, element):
        if type(element) == BeautifulSoup or type(element) == Tag:
            return element
        else:
            return BeautifulSoup(element, 'lxml')


class Bs4AttrField(_Bs4Field):

    def __init__(
            self,
            target: str,
            name: Union[str, list, Pattern, bool] = None,
            attrs: dict = None,
            recursive: bool = True,
            string: Union[str, list, Pattern, bool] = None,
            css_select: str = None,
            default=None,
            many: bool = True,
            next_request: bool = False,
            url_prefix: str = None
    ):
        super(Bs4AttrField, self).__init__(
            name=name,
            attrs=attrs,
            recursive=recursive,
            string=string,
            default=default,
            css_select=css_select,
            many=many,
            next_request=next_request,
            url_prefix=url_prefix
        )
        self.target = target

    def _parse_element(self, element):
        return element.get(self.target, self.default)


class Bs4TextField(_Bs4Field):

    def __init__(
            self,
            separator: str = None,
            name: Union[str, list, Pattern, bool] = None,
            attrs: dict = None,
            recursive: bool = True,
            string: Union[str, list, Pattern, bool] = None,
            css_select: str = None,
            default=None,
            many: bool = True,
            next_request: bool = False,
            url_prefix: str = None
    ):
        super(Bs4TextField, self).__init__(
            name=name,
            attrs=attrs,
            recursive=recursive,
            string=string,
            css_select=css_select,
            default=default,
            many=many,
            next_request=next_request,
            url_prefix=url_prefix
        )
        self.separator = separator

    def _parse_element(self, element):
        if self.separator:
            string = element.get_text(self.separator, strip=True)
        else:
            string = element.get_text(strip=True)
        if not string:
            return self.default
        else:
            string = re.sub(r'\s+', '', string)
            return string


class Bs4AttrTextField(_Bs4Field):

    def __init__(
            self,
            target: str,
            separator: str = None,
            name: Union[str, list, Pattern, bool] = None,
            attrs: dict = None,
            recursive: bool = True,
            string: Union[str, list, Pattern, bool] = None,
            css_select: str = None,
            default=None,
            many: bool = True,
            next_request: bool = False,
            url_prefix: str = None
    ):
        super(Bs4AttrTextField, self).__init__(
            name=name,
            attrs=attrs,
            recursive=recursive,
            string=string,
            default=default,
            css_select=css_select,
            many=many,
            next_request=next_request,
            url_prefix=url_prefix
        )
        self.target = target
        self.separator = separator

    def _parse_element(self, element):
        attr = element.get(self.target, self.default)
        if self.separator:
            string = element.get_text(self.separator, strip=True)
        else:
            string = element.get_text(strip=True)
        if not string:
            text = self.default
        else:
            text = re.sub(r'\s+', '', string)

        data = {'text': text, 'attr': attr}
        return data


class _LxmlElementField(BaseField):

    def __init__(self, css_select: str = None, xpath_select: str = None, default=None, many: bool = False, next_request: bool = False, url_prefix: str = None):
        super(_LxmlElementField, self).__init__(default=default, many=many, next_request=next_request, url_prefix=url_prefix)
        self.css_select = css_select
        self.xpath_select = xpath_select

    def extract(self, html_etree: etree._Element, is_source: bool = False):
        elements = self._get_elements(html_etree=html_etree)
        # 如果是target_item，则表明是一个预先提取的部分，为source
        if is_source:
            return elements if self.many else elements[0]

        # 如果不是target_item，但通过css_select或xpath_select提取出来的elements有值
        if elements:
            # 则根据子类AttrField，HtmlField，TextField重写的_parse_element()方法，提取出elements集合
            results = [self._parse_element(element) for element in elements]
        elif self.default is None:
            # 如果self.default则返回错误提示：_LxmlElementField需要有selector或者default值
            raise NothingMatchedError(
                f"Extract `{self.css_select or self.xpath_select}` error, "
                f"please check selector or set parameter named `default`"
            )
        else:
            # 如果如果不是target_item，也没有通过css_select或xpath_select提取出来的elements，也没有传递进来的default值
            # 则返回default=None
            results = self.default if type(self.default) == list else [self.default]
        # 如果self.many为True, 则返回results集合，否则返回results集合中的第一个元素
        return results if self.many else results[0]

    def _get_elements(self, *, html_etree: etree._Element):
        if self.css_select:                                           # 如果self.css_select为True, 则使用cssselect()方法来提取elements, etree会匹配所有符合条件的dom
            elements = html_etree.cssselect(self.css_select)
        elif self.xpath_select:                                       # 如果self.xpath_select为True, 则使用xpath()方法来提取elements, etree会匹配所有符合条件的dom
            elements = html_etree.xpath(self.xpath_select)
        else:
            raise ValueError(f"{self.__class__.__name__} field: css_select or xpath_select is expected")
        if not self.many:                                             # 如果self.many不为True, 则返回elements的第一个记录， 否则全部返回
            elements = elements[:1]
        return elements

    def _parse_element(self, element):
        raise NotImplementedError


class AttrField(_LxmlElementField):
    def __init__(self, attr, css_select: str = None, xpath_select: str = None, default="", many: bool = False, next_request: bool = False, url_prefix: str = None):
        super(AttrField, self).__init__(css_select=css_select, xpath_select=xpath_select, default=default, many=many, next_request=next_request, url_prefix=url_prefix)
        self.attr = attr

    def _parse_element(self, element):
        return element.get(self.attr, self.default)


class HtmlField(_LxmlElementField):
    def _parse_element(self, element):
        return etree.tostring(element, encoding="utf-8").decode(encoding="utf-8")


class TextField(_LxmlElementField):
    def _parse_element(self, element):
        if isinstance(element, etree._ElementUnicodeResult):
            strings = [node for node in element]
        else:
            strings = [node.strip() for node in element.itertext()]
        string = "".join(strings)
        return string if string else self.default


class RegexField(BaseField):
    def __init__(self, re_select: str, re_flags=0, default="", many: bool = False, next_request: bool = False, url_prefix: str = None):
        super(RegexField, self).__init__(default=default, many=many, next_request=next_request, url_prefix=url_prefix)
        self._re_select = re_select
        self._re_object = re.compile(self._re_select, flags=re_flags)

    def _parse_match(self, match):
        if not match:
            if self.default:
                return self.default
            else:
                raise NothingMatchedError(
                    f"Extract `{self._re_select}` error, "
                    f"please check selector or set parameter named `default`"
                )
        else:
            string = match.group()
            groups = match.groups()
            group_dict = match.groupdict()
            if group_dict:
                return group_dict
            if groups:
                return groups[0] if len(groups) == 1 else groups
            return string

    def extract(self, html: Union[str, etree._Element, BeautifulSoup, Tag]):
        if isinstance(html, etree._Element):                                # 如果html是etree._Element实例，则将其转为string格式
            html = etree.tostring(html).decode(encoding="utf-8")
        elif isinstance(html, BeautifulSoup) or isinstance(html, Tag):
            html = html.prettify()

        if self.many:                                                       # 如果many是True, 则多处匹配正则寻找
            matches = self._re_object.finditer(html)
            return [self._parse_match(match) for match in matches]
        else:                                                               # 如果不是many, 则仅使用正则的search()方法寻找单处
            match = self._re_object.search(html)
            return self._parse_match(match)


class JsonField(BaseField):
    def __init__(self, json_select: str = None, default=None, many: bool = False, next_request: bool = False, url_prefix: str = None):
        super(JsonField, self).__init__(default=default, many=many, next_request=next_request, url_prefix=url_prefix)
        self.json_select = json_select

    # 根据json_select的层级数，一层一层的提取json数据，例如json_select="a>b>c"
    def _get_elements(self, jsondata: json):
        if not self.json_select:
            return self.default

        list_select = self.json_select.split('>')
        for one in list_select:
            jsondata = jsondata[one]
        return jsondata

    # 根据json_select，从json数据中，提取出值，例如title = JsonField(json_select="e")
    def extract(self, jsondata: json):
        return self._get_elements(jsondata=jsondata)
