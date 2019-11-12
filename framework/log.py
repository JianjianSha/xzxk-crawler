import logging
import logging.handlers
import os

# logger registration
logger_dict = {}

def get_logger(filename):
    if filename in logger_dict:
        return logger_dict[filename]
        
    assert filename[0] == '/'
    
    segs = filename.split('/')
    logger_name = 'default'
    for i in range(len(segs)):
        if segs[i] == 'log' and i+1 < len(segs):
            logger_name = segs[i+1][:-4]    # remote '.log' ext

    if logger_name in logger_dict:
        return logger_dict[logger_name]

    logger = logging.getLogger(logger_name)
    file_handler = logging.handlers.RotatingFileHandler(filename,
                                                        mode='w',
                                                        maxBytes=1024*1024,
                                                        backupCount=5,
                                                        encoding='utf-8')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger_dict[logger_name] = logger
    return logger