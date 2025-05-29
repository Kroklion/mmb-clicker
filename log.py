import logging
from .uisettings import ClickerPreferences

logger: logging.Logger
logger_name: str


def debug(msg: str):
    logger.debug(msg, stacklevel=2)

def info(msg: str):
    logger.info(msg, stacklevel=2)

def warning(msg: str):
    logger.warning(msg, stacklevel=2)
    
def error(msg: str):
    logger.error(msg, stacklevel=2)


def init_logger(name: str):
    global logger_name
    global logger
    logger_name = name
    logger = logging.getLogger(name)
    logger.setLevel('DEBUG')

    streamhandler = logging.StreamHandler()

    formatter = logging.Formatter(
        '%(levelname)8s|%(filename)14s|%(name)s|%(funcName)22s()|%(message)s')

    streamhandler.setFormatter(formatter)

    logger.addHandler(streamhandler)

def debug_level_cb(new_level: str):
    logger.setLevel(new_level)
    logger.info('Log level set to ' + new_level)
    
def setup_preferences_cb():
    ClickerPreferences.register_callback('debug_level', debug_level_cb)
    logger.debug('logger was set up ' + __package__)
    pass


def uninit_logger():
    logger.debug('removing the logger ' + logger_name)
    if logger_name in logging.Logger.manager.loggerDict:
        del logging.Logger.manager.loggerDict[logger_name]
