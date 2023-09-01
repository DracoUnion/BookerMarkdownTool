import tempfile
import uuid
import subprocess as subp
import re
import sys
import os
import shutil
import json
import yaml
import traceback
from functools import reduce
from urllib.parse import quote_plus
from os import path
from pyquery import PyQuery as pq
from datetime import datetime
from collections import OrderedDict
import imgyaso

DIR = path.dirname(path.abspath(__file__))

default_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
}

headers = {
    'User-Agent': 'PostmanRuntime/7.26.8',
    'Referer': 'https://www.bilibili.com/',
}

def d(name):
    return path.join(DIR, name)

def asset(name=''):
    return path.join(DIR, 'assets', name)

def opti_img(img, mode, colors):
    if mode == 'quant':
        return imgyaso.pngquant_bts(img, colors)
    elif mode == 'grid':
        return imgyaso.grid_bts(img)
    elif mode == 'trunc':
        return imgyaso.trunc_bts(img, colors)
    elif mode == 'thres':
        return imgyaso.adathres_bts(img)
    else:
        return img


def fname_escape(name):
    return name.replace('\\', '＼') \
               .replace('/', '／') \
               .replace(':', '：') \
               .replace('*', '＊') \
               .replace('?', '？') \
               .replace('"', '＂') \
               .replace('<', '＜') \
               .replace('>', '＞') \
               .replace('|', '｜')
               
    
def safe_mkdir(dir):
    try: os.makedirs(dir)
    except: pass
    
def safe_rmdir(dir):
    try: shutil.rmtree(dir)
    except: pass

def is_c_style_code(fname):
    ext = [
        'c', 'cpp', 'cxx', 'h', 'hpp',
        'java', 'kt', 'scala', 
        'cs', 'js', 'json', 'ts', 
        'php', 'go', 'rust', 'swift',
    ]
    m = re.search(r'\.(\w+)$', fname)
    return bool(m and m.group(1) in ext)

def is_pic(fname):
    ext = [
        'jpg', 'jpeg', 'jfif', 'png', 
        'gif', 'tiff', 'webp'
    ]
    m = re.search(r'\.(\w+)$', fname)
    return bool(m and m.group(1) in ext)

def find_cmd_path(name):
    for p in os.environ.get('PATH', '').split(';'):
        if path.isfile(path.join(p, name)) or \
            path.isfile(path.join(p, name + '.exe')):
            return p
    return ''
    
def is_video(fname):
    ext = [
        'mp4', 'm4v', '3gp', 'mpg', 'flv', 'f4v', 
        'swf', 'avi', 'gif', 'wmv', 'rmvb', 'mov', 
        'mts', 'm2t', 'webm', 'ogg', 'mkv', 'mp3', 
        'aac', 'ape', 'flac', 'wav', 'wma', 'amr', 'mid',
    ]
    m = re.search(r'\.(\w+)$', fname)
    return bool(m and m.group(1) in ext)
    
def dict_get_recur(obj, keys):
    res = [obj]
    for k in keys.split('.'):
        k = k.strip()
        if k == '*':
            res = reduce(lambda x, y: x + y,res, [])
        else:
            res = [o.get(k) for o in res if k in o]
    return res
    
def safe(default=None):
    def outer(f):
        def inner(*args, **kw):
            print(123123)
            try: return f(*args, **kw)
            except: 
                traceback.print_exc()
                return default
        return inner
    return outer

def find_cmd_path(name):
    delim = ';' if sys.platform == 'win32' else ':'
    suff = (
        ['.exe', '.cmd', '.ps1']
        if sys.platform == 'win32'
        else ['', '.sh']
    ) 
    for p in os.environ.get('PATH', '').split(delim):
        if any(path.isfile(path.join(p, name + s)) for s in suff):
            return p
    return ''
