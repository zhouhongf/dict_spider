import os
import sys


class Config:

    PROJECT_NAME = 'ubank_local'

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    ROOT_DIR = os.path.dirname(BASE_DIR)

    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    os.makedirs(LOG_DIR, exist_ok=True)

    TIMEZONE = 'Asia/Shanghai'
    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36'

    SCHEDULED_DICT = {
        'time_interval': int(os.getenv('TIME_INTERVAL', 720)),              # 定时爬取代理数据时间
    }

    HOST_LOCAL = '192.168.3.250'
    MONGO_DICT = {
        'host': HOST_LOCAL,
        'port': 27017,
        'db': PROJECT_NAME,
        'username': 'root',
        'password': '123456',
    }




