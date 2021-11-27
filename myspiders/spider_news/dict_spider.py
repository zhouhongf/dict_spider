from myspiders.base import Spider
from config import Rules, Target, Vocabulary
from urllib.parse import urlencode, urlparse, urljoin, quote, unquote
import re


class DictSpider(Spider):
    name = 'DictSpider'
    targets = Rules.RULES_DICT

    async def parse(self, response):
        url_old = response.url
        domain = urlparse(url_old).netloc

        html = await response.text()
        target: Target = response.metadata['target']

        list_chapter = target.selectors[0].extract(soup=html)
        for one in list_chapter:
            url = urljoin(url_old, one)
            yield self.request(url=url, callback=self.parse_next, metadata={'target': target})

    async def parse_next(self, response):
        target: Target = response.metadata['target']
        url_old = response.url
        param = url_old.split('&')[-1]
        class_id = param.split('=')[-1]

        url_prefix = 'http://word.iciba.com/?action=words&class=%s&course=%s'
        html = await response.text()
        list_chapter = target.selectors[1].extract(soup=html)
        if len(list_chapter) > 0:
            for i in range(1, len(list_chapter) + 1):
                url = url_prefix % (class_id, i)
                yield self.request(url=url, callback=self.parse_final, metadata={'target': target})

    async def parse_final(self, response):
        target: Target = response.metadata['target']
        html = await response.text()
        selector_english = target.selectors[3]
        selector_chinese = target.selectors[4]
        selector_phonetic = target.selectors[5]
        selector_voice = target.selectors[6]

        list_row = target.selectors[2].extract(soup=html)
        for one in list_row:
            english = selector_english.extract(soup=one)
            chinese = selector_chinese.extract(soup=one)
            phonetic = selector_phonetic.extract(soup=one)
            voice = selector_voice.extract(soup=one)

            chinese = re.sub(r'\s+', '', chinese)
            vocabulary = Vocabulary(name_english=english, name_chinese=chinese, phonetic=phonetic, voice=voice)
            await self.save_db(vocabulary)

    async def save_db(self, vocabulary: Vocabulary):
        data = vocabulary.do_dump()
        self.mongo.do_insert_one(self.collection,  {'_id': data['_id']}, data)


def start():
    DictSpider.start()






