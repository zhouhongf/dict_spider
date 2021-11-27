import os
import sys
import time
from config import Config
import schedule
from myspiders.spider_console import spider_console


# 将scheduled_task.py文件所在的目录的绝对路径添加到环境变量中去
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def refresh_task(time_interval):
    schedule.every(time_interval).minutes.do(spider_console)
    time.sleep(2)

    while True:
        schedule.run_pending()
        time.sleep(5)


if __name__ == '__main__':
    spider_console()
    time.sleep(2)

    # time_interval = Config.SCHEDULED_DICT['time_interval']
    # refresh_task(time_interval=time_interval)
