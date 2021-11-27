#!/usr/bin/env python3
import re
import time
import traceback

import cchardet
import lxml
import lxml.html
from lxml.html import HtmlComment


# REGEXES收集了一些经常出现在标签的class和id中的关键词，这些词标识着该标签可能是正文或者不是。
# 用这些词来给标签节点计算权重，也就是方法calc_node_weight()的作用。
REGEXES = {
    'positiveRe': re.compile(
        ('article|arti|body|content|entry|hentry|main|page|'
         'artical|zoom|arti|context|message|editor|'
         'pagination|post|txt|text|blog|story'), re.I),
    'negativeRe': re.compile(
        ('copyright|combx|comment|com-|contact|foot|footer|footnote|decl|copy|'
         'notice|'
         'masthead|media|meta|outbrain|promo|related|scroll|link|pagebottom|bottom|'
         'other|shoutbox|sidebar|sponsor|shopping|tags|tool|widget'), re.I),
}


class MainContent:
    def __init__(self,):
        # 初始化，先定义了一些不会包含正文的标签 self.non_content_tag，遇到这些标签节点，直接忽略掉即可。
        self.non_content_tag = set([
            'head',
            'meta',
            'script',
            'style',
            'object', 'embed',
            'iframe',
            'marquee',
            'select',
        ])
        self.title = ''
        self.p_space = re.compile(r'\s')
        self.p_content_stop = re.compile(r'正文.*结束|正文下|相关阅读|声明')
        self.p_clean_tree = re.compile(r'author|post-add|copyright')

    # 本算法提取标题实现在get_title()这个函数里面。
    def get_title(self, doc):
        title = ''
        # 首先，它先获得<title>标签的内容
        title_el = doc.xpath('//title')
        if title_el:
            title = title_el[0].text_content().strip()
        if len(title) < 7:
            # 然后, 试着从<meta>里面找title，
            tt = doc.xpath('//meta[@name="title"]')
            if tt:
                title = tt[0].get('content', '')
        if len(title) < 7:
            # 再尝试从<body>里面找id和class包含title的节点
            tt = doc.xpath('//*[contains(@id, "title") or contains(@class, "title")]')
            if not tt:
                tt = doc.xpath('//*[contains(@id, "font01") or contains(@class, "font01")]')
            # 最后把从不同地方获得的可能是标题的文本进行对比，最终获得标题。
            for t in tt:
                ti = t.text_content().strip()
                # (1)<meta>, <body>里面找到的疑似标题如果包含在<title>标签里面，则它是一个干净（没有频道名、网站名）的标题；
                if ti in title and len(ti)*2 > len(title):
                    title = ti
                    break
                # (2)如果疑似标题太长就忽略
                if len(ti) > 20: continue
                # (3)主要把<title>标签作为标题
                if len(ti) > len(title) or len(ti) > 7:
                    title = ti
        return title

    # 从<title>标签里面获得标题，就要解决标题清洗的问题。这里实现了一个简单的方法clean_title()。
    def clean_title(self, title):
        spliters = [' - ', '–', '—', '-', '|', '::']
        for s in spliters:
            if s not in title:
                continue
            tts = title.split(s)
            if len(tts) < 2:
                continue
            title = tts[0]
            break
        return title

    def calc_node_weight(self, node):
        weight = 1
        attr = '%s %s %s' % (
            node.get('class', ''),
            node.get('id', ''),
            node.get('style', '')
        )
        if attr:
            mm = REGEXES['negativeRe'].findall(attr)
            weight -= 2 * len(mm)
            mm = REGEXES['positiveRe'].findall(attr)
            weight += 4 * len(mm)
        if node.tag in ['div', 'p', 'table']:
            weight += 2
        return weight

    # 使用了lxml.html把网页的html转化成一棵树，
    # 从body节点开始遍历每一个节点，
    # 看它直接包含（不含子节点）的文本的长度，从中找出含有最长文本的节点。
    def get_main_block(self, url, html, clean_title=True):
        ''' return (title, etree_of_main_content_block)'''
        if isinstance(html, bytes):
            encoding = cchardet.detect(html)['encoding']
            if encoding is None:
                return None, None
            html = html.decode(encoding, 'ignore')
        try:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(base_url=url)
        except :
            traceback.print_exc()
            return None, None

        self.title = self.get_title(doc)
        if clean_title:
            self.title = self.clean_title(self.title)

        body = doc.xpath('//body')
        if not body:
            return self.title, None

        candidates = []
        nodes = body[0].getchildren()
        while nodes:
            # 一个接着一个取出node
            node = nodes.pop(0)
            children = node.getchildren()
            tlen = 0
            for child in children:
                if isinstance(child, HtmlComment):
                    continue
                if child.tag in self.non_content_tag:
                    continue
                if child.tag == 'a':
                    continue
                if child.tag == 'textarea':
                    # FIXME: this tag is only part of content?
                    continue
                attr = '%s%s%s' % (child.get('class', ''),
                                   child.get('id', ''),
                                   child.get('style'))
                if 'display' in attr and 'none' in attr:
                    continue

                nodes.append(child)

                if child.tag == 'p':
                    weight = 3
                else:
                    weight = 1

                text = '' if not child.text else child.text.strip()
                tail = '' if not child.tail else child.tail.strip()

                tlen += (len(text) + len(tail)) * weight

            if tlen < 10:
                continue

            weight = self.calc_node_weight(node)
            candidates.append((node, tlen*weight))

        if not candidates:
            return self.title, None

        candidates.sort(key=lambda a: a[1], reverse=True)

        good = candidates[0][0]
        if good.tag in ['p', 'pre', 'code', 'blockquote']:
            for i in range(5):
                good = good.getparent()
                if good.tag == 'div':
                    break

        good = self.clean_node(good, url)
        return self.title, good

    # clean_node()这个函数。通过get_main_block()得到的节点，
    # 有可能包含相关新闻的链接，这些链接包含大量新闻标题，如果不去除，就会给新闻内容带来杂质（相关新闻的标题、概述等）。
    def clean_node(self, tree, url=''):
        to_drop = []
        drop_left = False
        for node in tree.iterdescendants():
            if drop_left:
                to_drop.append(node)
                continue
            if isinstance(node, HtmlComment):
                to_drop.append(node)
                if self.p_content_stop.search(node.text):
                    drop_left = True
                continue
            if node.tag in self.non_content_tag:
                to_drop.append(node)
                continue
            attr = '%s %s' % (
                node.get('class', ''),
                node.get('id', '')
            )
            if self.p_clean_tree.search(attr):
                to_drop.append(node)
                continue
            aa = node.xpath('.//a')
            if aa:
                text_node = len(self.p_space.sub('', node.text_content()))
                text_aa = 0
                for a in aa:
                    alen = len(self.p_space.sub('', a.text_content()))
                    if alen > 5:
                        text_aa += alen
                if text_aa > text_node * 0.4:
                    to_drop.append(node)
        for node in to_drop:
            try:
                node.drop_tree()
            except:
                pass
        return tree

    # get_text()函数。我们从main block中提取文本内容，
    # 不是直接使用text_content()，而是做了一些格式方面的处理，
    # 比如在一些标签后面加入换行符合\n，在table的单元格之间加入空格。
    # 这样处理后，得到的文本格式比较符合原始网页的效果。
    def get_text(self, doc):
        lxml.etree.strip_elements(doc, 'script')
        lxml.etree.strip_elements(doc, 'style')
        for ch in doc.iterdescendants():
            if not isinstance(ch.tag, str):
                continue
            if ch.tag in ['div', 'h1', 'h2', 'h3', 'p', 'br', 'table', 'tr', 'dl']:
                if not ch.tail:
                    ch.tail = '\n'
                else:
                    ch.tail = '\n' + ch.tail.strip() + '\n'
            if ch.tag in ['th', 'td']:
                if not ch.text:
                    ch.text = '  '
                else:
                    ch.text += '  '
            # if ch.tail:
            #     ch.tail = ch.tail.strip()
        lines = doc.text_content().split('\n')
        content = []
        for l in lines:
            l = l.strip()
            if not l:
                continue
            content.append(l)
        return '\n'.join(content)

    def extract(self, url, html):
        '''return (title, content)'''
        title, node = self.get_main_block(url, html)
        if node is None:
            print('\tno main block got !!!!!', url)
            return title, '', ''
        content = self.get_text(node)
        return title, content


if __name__ == '__main__':
    from sys import argv
    f = argv[1]
    html = open(f, 'rb').read()
    encoding = cchardet.detect(html)
    print('encoding:', encoding)
    encoding = encoding['encoding']
    html = html.decode(encoding, 'ignore')
    mc = MainContent()
    b = time.time()
    t, c = mc.extract('', html)
    e = time.time()
    print('title:', t)
    print('content:', len(c))
    print('time cost: ', e-b)
    title, content = t, c
    txt = 'title:%s\ncontent:\n%s\n\n' % (
        title,
        content,
    )
    open(f+'-content2.txt','w').write(txt)
