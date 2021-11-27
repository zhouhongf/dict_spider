import aiofiles
import os
import aiohttp
import asyncio
import async_timeout
import random
from config import Config
import re
from urllib.parse import urlencode, urlparse, urljoin, quote, unquote, urlunparse

try:
    from ujson import loads as json_loads
except:
    from json import loads as json_loads


# 供 client_manual下载PDF时需要cookie使用
splash_url = 'http://%s:8050/execute?lua_source=' % Config.HOST_LOCAL
lua_script = '''
function main(splash, args)
    local myheaders = {}
    myheaders['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36'
    assert(splash:go{'%s', headers=myheaders})
    assert(splash:wait(2))
    return {
        html = splash:html(),
        cookies = splash:get_cookies(),
    }
end'''

suffix_check = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.html', '.htm', '.shtml', '.shtm', '.zip', '.rar', '.tar', '.bz2', '.7z', '.gz']
suffix_file = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.zip', '.rar', '.tar', '.bz2', '.7z', '.gz']


cookie_url_spdb = 'https://per.spdb.com.cn/bank_financing/financial_product'


async def fetch_bank_cookies(bank_name):
    cookie = ''
    if bank_name == '浦发银行':
        cookie = await fetch_cookies_spdb()

    return cookie


async def fetch_cookies_by_splash(client, url, timeout=15):
    with async_timeout.timeout(timeout):
        try:
            async with client.get(url, timeout=timeout) as response:
                return await response.json()
        except Exception as e:
            print('无法获取cookie, url是：', url)
            return None


async def fetch_cookies_spdb():
    lua = lua_script % cookie_url_spdb
    url = splash_url + quote(lua)
    async with aiohttp.ClientSession() as client:
        jsondata = await fetch_cookies_by_splash(client, url)
        if not jsondata:
            return None

        cookies = jsondata['cookies']
        if not cookies:
            return None

        query_set = set()
        for cookie in cookies:
            name = cookie['name'].strip()
            value = cookie['value'].strip()
            if name == 'TSPD_101' or name == 'TS01d02f4c' or name == 'WASSESSION':
                query = name + '=' + value + ';'
                query_set.add(query)
            elif name.startswith('Hm_lvt_') or name.startswith('Hm_lpvt_'):
                query = name + '=' + value + ';'
                query_set.add(query)
        cookie_need = ''
        for query in query_set:
            cookie_need += query
        print('获取到的浦发银行Cookie是：%s' % cookie_need)
        return cookie_need



async def fetch(client, url, proxy=None, params=None, timeout=15):
    if params is None:
        params = {}
    with async_timeout.timeout(timeout):
        try:
            headers = {'user-agent': await get_random_user_agent()}
            async with client.get(url, headers=headers, proxy=proxy, params=params, timeout=timeout) as response:
                assert response.status == 200
                try:
                    text = await response.text()
                except:
                    text = await response.read()
                return text
        except Exception as e:
            return None


async def request_html_by_aiohttp(url, proxy=None, params=None, timeout=15):
    if params is None:
        params = {}
    async with aiohttp.ClientSession() as client:
        html = await fetch(client=client, url=url, proxy=proxy, params=params, timeout=timeout)
        return html if html else None


async def get_random_user_agent():
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36'
    return random.choice(await _get_data('user_agents.txt', user_agent))


async def _get_data(filename, default=''):
    root_folder = os.path.dirname(__file__)
    user_agents_file = os.path.join(root_folder, filename)
    try:
        async with aiofiles.open(user_agents_file, mode='r') as f:
            data = [_.strip() for _ in await f.readlines()]
    except:
        data = [default]
    return data


def screen_size():
    """使用tkinter获取屏幕大小"""
    import tkinter
    tk = tkinter.Tk()
    width = tk.winfo_screenwidth()
    height = tk.winfo_screenheight()
    tk.quit()
    return width, height



g_bin_postfix = set([
    'exe', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'pdf',
    'jpg', 'png', 'bmp', 'jpeg', 'gif',
    'zip', 'rar', 'tar', 'bz2', '7z', 'gz',
    'flv', 'mp4', 'avi', 'wmv', 'mkv',
    'apk',
])

g_news_postfix = ['.html?', '.htm?', '.shtml?', '.shtm?']

g_pattern_tag_a = re.compile(r'<a[^>]*?href=[\'"]?([^> \'"]+)[^>]*?>(.*?)</a>', re.I | re.S | re.M)


# 按照设定的规则，过滤出来需要的url链接
def clean_url(url):
    # 1. 是否为合法的http url
    if not url.startswith('http'):
        return ''
    # 2. 去掉静态化url后面的参数
    for np in g_news_postfix:
        p = url.find(np)
        if p > -1:
            p = url.find('?')
            url = url[:p]
            return url
    # 3. 不下载二进制类内容的链接
    up = urlparse(url)
    path = up.path
    if not path:
        path = '/'
    postfix = path.split('.')[-1].lower()
    if postfix in g_bin_postfix:
        return ''

    # 4. 去掉标识流量来源的参数
    # badquery = ['spm', 'utm_source', 'utm_source', 'utm_medium', 'utm_campaign']
    good_queries = []
    for query in up.query.split('&'):
        qv = query.split('=')
        if qv[0].startswith('spm') or qv[0].startswith('utm_'):
            continue
        if len(qv) == 1:
            continue
        good_queries.append(query)
    query = '&'.join(good_queries)
    url = urlunparse((
        up.scheme,
        up.netloc,
        path,
        up.params,
        query,
        ''  # crawler do not care fragment
    ))
    return url


def extract_links_re(url, html):
    '''use re module to extract links from html'''
    newlinks = set()
    aa = g_pattern_tag_a.findall(html)
    for a in aa:
        link = a[0].strip()
        if not link:
            continue
        link = urljoin(url, link)
        link = clean_url(link)
        if not link:
            continue
        newlinks.add(link)
    return newlinks


if __name__ == '__main__':
    import asyncio
    print(asyncio.get_event_loop().run_until_complete(get_random_user_agent()))

