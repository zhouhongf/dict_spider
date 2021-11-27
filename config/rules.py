#!/usr/bin/env python
from collections import namedtuple
from urllib.parse import urlencode, urlparse, urljoin, quote, unquote
from myspiders.base import BaseField, Bs4TextField, Bs4HtmlField, Bs4AttrField, Bs4AttrTextField, JsonField, TextField, HtmlField, AttrField
import re
import time
from .target import Target


class Rules:
    pattern_string = re.compile(r'^((?!(【详情】|【详细】|更多)).)*$')
    pattern_date = re.compile(r'20[0-9]{2}[-年/][01]?[0-9][-月/][0123]?[0-9]日?')
    pattern_sina = re.compile(r'https://finance.sina.com.cn/.+/doc-.+\.(shtml|shtm|html|htm)')

    RULES_DICT = {
        Target(
            bank_name='金山词霸',
            type_main='英语',
            type_next='英汉单词',
            url='http://word.iciba.com/',
            selectors=[
                Bs4AttrField(target='href', name='a', attrs={'href': re.compile(r'action=courses&classid=')}, next_request=True, many=True),
                Bs4HtmlField(name='li', attrs={'class': 'c_panel', 'course_id': re.compile(r'\d+')}, next_request=True, many=True),
                Bs4HtmlField(css_select='.word_main_list li', next_request=False, many=True),
                Bs4AttrField(target='title', css_select='div.word_main_list_w span', next_request=False, many=False),
                Bs4AttrField(target='title', css_select='div.word_main_list_s span', next_request=False, many=False),
                Bs4TextField(css_select='div.word_main_list_y strong', next_request=False, many=False),
                Bs4AttrField(target='id', css_select='div.word_main_list_y a', next_request=False, many=False),
            ]
        ),
    }



    RULES_NEWS = {
        Target(
            bank_name='新浪财经',
            type_main='新闻',
            type_next='首页要闻',
            url='http://finance.sina.com.cn/money/bank/',
            selectors=[
                Bs4AttrTextField(target='href', name='a', attrs={'href': pattern_sina}, string=pattern_string, next_request=True),
            ]
        ),
        Target(
            bank_name='新浪财经',
            type_main='新闻',
            type_next='监管政策',
            url='http://finance.sina.com.cn/roll/index.d.html?cid=56689&page=1',
            selectors=[
                Bs4AttrTextField(target='href', name='a', attrs={'href': pattern_sina}, string=pattern_string, next_request=True),
            ]
        ),
        Target(
            bank_name='新浪财经',
            type_main='新闻',
            type_next='公司动态',
            url='http://finance.sina.com.cn/roll/index.d.html?cid=80798&page=1',
            selectors=[
                Bs4AttrTextField(target='href', name='a', attrs={'href': pattern_sina}, string=pattern_string, next_request=True),
            ]
        ),
        Target(
            bank_name='新浪财经',
            type_main='新闻',
            type_next='产品业务',
            url='http://finance.sina.com.cn/roll/index.d.html?cid=56693&page=1',
            selectors=[
                Bs4AttrTextField(target='href', name='a', attrs={'href': pattern_sina}, string=pattern_string, next_request=True),
            ]
        ),
        Target(
            bank_name='新浪财经',
            type_main='新闻',
            type_next='理财要闻',
            url='http://finance.sina.com.cn/money/',
            selectors=[
                Bs4HtmlField(attrs={'id': re.compile(r'subShowContent1_news[0-9]')}),
                Bs4AttrTextField(target='href', name='a', attrs={'href': pattern_sina}, string=pattern_string, next_request=True),
            ]
        ),
        Target(
            bank_name='新浪财经',
            type_main='新闻',
            type_next='理财要闻',
            url='http://finance.sina.com.cn/money/',
            selectors=[
                Bs4AttrTextField(target='href',
                                 css_select='div[id^="subShowContent1_news"] .news-item h2 a[href*="/doc-"]',
                                 next_request=True),
            ]
        ),
    }

    # 每次仅爬取首页内容
    RULES = {
        Target(
            bank_name='工商银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.icbc.com.cn/icbc/%e5%b7%a5%e8%a1%8c%e9%a3%8e%e8%b2%8c/%e5%b7%a5%e8%a1%8c%e5%bf%ab%e8%ae%af/default.htm',
            selectors=[
                Bs4AttrTextField(target='href', attrs={'class': 'data-collecting-sign textgs'}, next_request=True),
                Bs4HtmlField(attrs={'id': 'MyFreeTemplateUserControl'}, many=False)
            ]
        ),
        Target(
            bank_name='中国银行',
            type_main='新闻',
            type_next='来源本行',
            url='https://www.boc.cn/aboutboc/bi1/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.news ul.list li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|content con_area')}, many=False)
            ]
        ),
        Target(
            bank_name='中国银行',
            type_main='公告',
            type_next='其他公告',
            url='https://www.boc.cn/custserv/bi2/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.news ul.list li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|content con_area')}, many=False)
            ]
        ),
        Target(
            bank_name='中国银行',
            type_main='公告',
            type_next='招聘公告',
            url='https://www.boc.cn/aboutboc/bi4/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.news ul.list li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|content con_area')}, many=False)
            ]
        ),
        Target(
            bank_name='中国银行',
            type_main='公告',
            type_next='采购公告',
            url='https://www.boc.cn/aboutboc/bi6/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.news ul.list li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|content con_area|')}, many=False)
            ]
        ),
        Target(
            bank_name='农业银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.abchina.com/cn/AboutABC/nonghzx/NewsCenter/default.htm',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.details_rightC.fl a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|details_rightWrapC')}, many=False)
            ]
        ),
        Target(
            bank_name='农业银行',
            type_main='公告',
            type_next='采购公告',
            url='http://www.abchina.com/cn/AboutABC/CG/BM/default.htm',
            selectors=[
                Bs4AttrTextField(target='href', name='a', attrs={'href': re.compile(r'\.htm|\.html')}, string=re.compile(r'公告'), next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|content_right_detail')}, many=False)
            ]
        ),
        Target(
            bank_name='农业银行',
            type_main='公告',
            type_next='采购公告',
            url='http://www.abchina.com/cn/AboutABC/CG/Purchase/default.htm',
            selectors=[
                Bs4AttrTextField(target='href', name='a', attrs={'href': re.compile(r'\.htm|\.html')}, string=re.compile(r'公告'), next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|content_right_detail')}, many=False)
            ]
        ),
        # 建设银行 的还有各省份分行 分支 有待爬取
        Target(
            bank_name='建设银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.ccb.com/cn/v3/include/notice/zxgg_1.html',
            selectors=[
                Bs4AttrTextField(target='href', name='a', attrs={'href': re.compile(r'\.htm|\.html'), 'class': 'blue3', 'title': True}, next_request=True),
                Bs4HtmlField(attrs={'id': 'ti'}, many=False)
            ]
        ),
        Target(
            bank_name='交通银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.bankcomm.com/BankCommSite/shtml/jyjr/cn/7158/7162/list_1.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.main ul.tzzgx-conter.ty-list li a', next_request=True),
                Bs4HtmlField(attrs={'class': 'show_main c_content'}, many=False)
            ]
        ),
        Target(
            bank_name='邮储银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.psbc.com/cn/index/syycxw/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#article_1 li.clearfix a', next_request=True),
                Bs4HtmlField(attrs={'class': 'news_cont_msg'}, many=False)
            ]
        ),
        Target(
            bank_name='邮储银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.psbc.com/cn/index/ggl/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#article_1 li.clearfix a', next_request=True),
                Bs4HtmlField(attrs={'class': 'news_cont_msg'}, many=False)
            ]
        ),
        Target(
            bank_name='邮储银行',
            type_main='公告',
            type_next='招聘公告',
            url='http://www.psbc.com/cn/index/rczp/rczygg/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#article_1 li.clearfix a', next_request=True),
                Bs4HtmlField(attrs={'class': 'news_cont_msg'}, many=False)
            ]
        ),

        Target(
            bank_name='中信银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.citicbank.com/about/companynews/banknew/message/%s/index.html' % time.strftime('%Y'),
            selectors=[
                Bs4AttrTextField(target='href', css_select='#business ul.dhy_b li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|main_content')}, many=False)
            ]
        ),
        Target(
            bank_name='中信银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.citicbank.com/about/companynews/zxsh/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#business ul.dhy_b li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|main_content')}, many=False)
            ]
        ),
        Target(
            bank_name='中信银行',
            type_main='公告',
            type_next='服务公告',
            url='http://www.citicbank.com/common/servicenotice/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#business ul.dhy_b li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|main_content')}, many=False)
            ]
        ),
        Target(
            bank_name='招商银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.cmbchina.com/cmbinfo/news/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#column_content span.c_title a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'infodiv|c_content')}, many=False)
            ]
        ),
        Target(
            bank_name='招商银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.cmbchina.com/main/default.aspx',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#ContentPlaceHolder1_listPromotion tr td li a', next_request=True),
                Bs4HtmlField(css_select='.notice .infocontainer', many=False)
            ]
        ),
        Target(
            bank_name='民生银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.cmbc.com.cn/jrms/msdt/msxw/index.htm',
            selectors=[
                Bs4AttrTextField(target='href', css_select='li.left_ul520 a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'counter_mid|counter_mid_1')}, many=False)
            ]
        ),
        Target(
            bank_name='民生银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.cmbc.com.cn/jrms/msdt/mtgz/index.htm',
            selectors=[
                Bs4AttrTextField(target='href', css_select='li.left_ul520 a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'counter_mid|counter_mid_1')}, many=False)
            ]
        ),
        Target(
            bank_name='民生银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.cmbc.com.cn/zdtj/zygg/index.htm',
            selectors=[
                Bs4AttrTextField(target='href', css_select='li.left_ul520 a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'counter_mid|counter_mid_1')}, many=False)
            ]
        ),
        Target(
            bank_name='民生银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.cmbc.com.cn/jrms/msdt/fykyzq/index.htm',
            selectors=[
                Bs4AttrTextField(target='href', css_select='li.left_ul520 a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'counter_mid|counter_mid_1')}, many=False)
            ]
        ),
        # 浦发银行的采购公告是PDF文件格式，后期再添加解析PDF文件的功能
        Target(
            bank_name='浦发银行',
            type_main='新闻',
            type_next='来源本行',
            url='https://news.spdb.com.cn/about_spd/xwdt_1632/index.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.c_news_body ul li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|c_article')}, many=False)
            ]
        ),
        Target(
            bank_name='浦发银行',
            type_main='新闻',
            type_next='来源本行',
            url='https://news.spdb.com.cn/about_spd/media/index.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.c_news_body ul li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|c_article')}, many=False)
            ]
        ),

        Target(
            bank_name='兴业银行',
            type_main='新闻',
            type_next='来源本行',
            url='https://www.cib.com.cn/cn/aboutCIB/about/news/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.list-box .middle ul:nth-of-type(2) li a',
                                 next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'middle|detail-box')}, many=False)
            ]
        ),
        Target(
            bank_name='兴业银行',
            type_main='公告',
            type_next='其他公告',
            url='https://www.cib.com.cn/cn/aboutCIB/about/notice/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.list-box .middle ul:nth-of-type(2) li a',
                                 next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'middle|detail-box')}, many=False)
            ]
        ),

        Target(
            bank_name='平安银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://bank.pingan.com/ir/gonggao/xinwen/index.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.span10 ul.list li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'list_detail|span10')}, many=False)
            ]
        ),

        Target(
            bank_name='广发银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.cgbchina.com.cn/Channel/11625977',
            selectors=[
                Bs4AttrTextField(target='href', css_select='ul.newList li a', next_request=True),
                Bs4HtmlField(attrs={'id': 'textContent'}, many=False)
            ]
        ),
        Target(
            bank_name='广发银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.cgbchina.com.cn/Channel/11640277',
            selectors=[
                Bs4AttrTextField(target='href', css_select='ul.newList li a', next_request=True),
                Bs4HtmlField(attrs={'id': 'textContent'}, many=False)
            ]
        ),

        Target(
            bank_name='光大银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.cebbank.com/site/ceb/gddt/xnxw52/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#main_con ul.gg_right_ul li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'xilan_con|gd_xilan')}, many=False)
            ]
        ),
        Target(
            bank_name='光大银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.cebbank.com/site/ceb/gddt/mtgz/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#main_con ul.gg_right_ul li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'xilan_con|gd_xilan')}, many=False)
            ]
        ),
        Target(
            bank_name='光大银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.cebbank.com/site/zhpd/zxgg35/gdgg10/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#gg_right ul.gg_right_ul li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'xilan_con|gd_xilan')}, many=False)
            ]
        ),
        Target(
            bank_name='光大银行',
            type_main='公告',
            type_next='采购公告',
            url='http://www.cebbank.com/site/zhpd/zxgg35/cggg/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#gg_right ul.gg_right_ul li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'xilan_con|gd_xilan')}, many=False)
            ]
        ),
        Target(
            bank_name='光大银行',
            type_main='公告',
            type_next='采购公告',
            url='http://www.cebbank.com/site/zhpd/zxgg35/cgjggg/index.html',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#gg_right ul.gg_right_ul li a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'xilan_con|gd_xilan')}, many=False)
            ]
        ),
        Target(
            bank_name='华夏银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.hxb.com.cn/jrhx/hxzx/hxxw/index.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.pro_contlist ul li.pro_contli a', next_request=True),
                Bs4HtmlField(attrs={'id': 'content'}, many=False)
            ]
        ),
        Target(
            bank_name='华夏银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.hxb.com.cn/jrhx/khfw/zxgg/index.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.pro_contlist ul li.pro_contli a', next_request=True),
                Bs4HtmlField(attrs={'id': 'content'}, many=False)
            ]
        ),

        Target(
            bank_name='浙商银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.czbank.com/cn/pub_info/news/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#content dd a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|cdv_content')}, many=False)
            ]
        ),
        Target(
            bank_name='浙商银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.czbank.com/cn/pub_info/important_notice/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.list_content dd a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|cdv_content')}, many=False)
            ]
        ),
        Target(
            bank_name='浙商银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.czbank.com/cn/pub_info/Outside_reports/',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.list_content dd a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'TRS_Editor|cdv_content')}, many=False)
            ]
        ),

        Target(
            bank_name='恒丰银行',
            type_main='新闻',
            type_next='来源本行',
            url='http://www.hfbank.com.cn/gyhf/hfxw/index.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='#imgArticleList li h3 a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'articleCon|infoArticle')}, many=False)
            ]
        ),
        Target(
            bank_name='恒丰银行',
            type_main='公告',
            type_next='其他公告',
            url='http://www.hfbank.com.cn/gryw/yhgg/index.shtml',
            selectors=[
                Bs4AttrTextField(target='href', css_select='.annWrap li h3 a', next_request=True),
                Bs4HtmlField(attrs={'class': re.compile(r'articleCon|infoArticle')}, many=False)
            ]
        ),
    }
