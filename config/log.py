import logging
from logging import handlers
import os
from .config import Config


class Logger:

    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    fmt = '%(asctime)s - %(pathname)s[line:%(lineno)d] - [%(levelname)s]: %(message)s'

    log_file_name = os.path.join(Config.LOG_DIR, Config.PROJECT_NAME + '.log')

    def __init__(self, filename=None, level='info', when='D', backCount=3):
        # logging.basicConfig(format=self.logging_format, datefmt="%Y:%m:%d %H:%M:%S")  # 此为默认简单设定
        self.filename = filename or self.log_file_name
        self.logger = logging.getLogger(self.filename)
        format_str = logging.Formatter(self.fmt)                                # 设置日志格式
        self.logger.setLevel(self.level_relations.get(level))                   # 设置日志级别
        sh = logging.StreamHandler()                                            # 往屏幕上输出
        sh.setFormatter(format_str)                                             # 设置屏幕上显示的格式
        th = handlers.TimedRotatingFileHandler(filename=self.filename, when=when, backupCount=backCount, encoding='utf-8')   # 往文件里写入#指定间隔时间自动生成文件的处理器
        # 实例化TimedRotatingFileHandler
        # interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒
        # M 分
        # H 小时、
        # D 天、
        # W 每星期（interval==0时代表星期一）
        # midnight 每天凌晨
        th.setFormatter(format_str)                                             # 设置文件里写入的格式
        self.logger.addHandler(sh)                                              # 把对象加到logger里
        self.logger.addHandler(th)


if __name__ == '__main__':
    # logging.DEBUG, 所有debug, info, warning, error, critical 的log都会打印到控制台。
    # level = logging.info()的话，debug 的信息则不会输出到控制台。
    # 日志级别： debug < info < warning < error < critical
    log = Logger('all.log', level='debug')
    log.logger.debug('debug')
    log.logger.info('info')
    log.logger.warning('警告')
    log.logger.error('报错')
    log.logger.critical('严重')

    logerror = Logger('error.log', level='error').logger
    logerror.error('logerror的error')
    # 因为日志级别设置了error, 所以所有的高于该级别的日志，都不会被记录下来, 低于该级别的会被记录下来
    logerror.info('logerror的info')
    logerror.critical('logerror的critical')


