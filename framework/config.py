import yaml
from .easydict import EasyDict as edict
import json
import os

def load(filename):
    if not os.path.isabs(filename):
        raise ValueError("filename must be abspath, bug got %s" % filename)
    d = edict()
    with open(filename, 'r', encoding='utf-8') as f:
        y = yaml.load(f)
        d.update(y)
    return d


def dump(filename, d):
    if not os.path.isabs(filename):
        raise ValueError("filename must be abspath, bug got %s" % filename)

    with open(filename, 'w') as f:
        yaml.dump(d, f)