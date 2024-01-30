import tempfile
import uuid
import subprocess as subp
import re
import sys
import os
import shutil
import json
import yaml
import copy
import traceback
from functools import reduce
from urllib.parse import quote_plus
from os import path
from pyquery import PyQuery as pq
from datetime import datetime
from collections import OrderedDict
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
import imgyaso

DIR = path.dirname(path.abspath(__file__))

default_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
}

headers = {
    'User-Agent': 'PostmanRuntime/7.26.8',
    'Referer': 'https://www.bilibili.com/',
}

RE_TITLE = r'\A\s*^#+\x20+(.+?)$'

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

def make_dir_handle(file_handle):
    def file_handle_safe(*args, **kw):
        try: file_handle(*args, **kw)
        except: traceback.print_exc()
        
    def dir_handle(args):
        dir = args.fname
        fnames = os.listdir(dir)
        pool = ThreadPoolExecutor(args.threads)
        hdls = []
        for fname in fnames:
            args = copy.deepcopy(args)
            args.fname = path.join(dir, fname)
            pool.submit(file_handle_safe, args)
        for h in hdls: h.result()
        
    return dir_handle

def num2d_to_zh(num):
    digit_zh_table = '零一二三四五六七八九'
    ones = num % 10
    tens = num // 10 % 10
    if tens == 0:
        return digit_zh_table[ones]
    return (
        (digit_zh_table[tens] if tens != 1 else '')
        + '十' + 
        (digit_zh_table[ones] if ones != 0 else '')
    )

def num3d_to_zh(num):
    digit_zh_table = '零一二三四五六七八九'
    ones = num % 10
    tens = num // 10 % 10
    hectos = num // 100 % 10
    if hectos == 0:
        return num2d_to_zh(num)
    if ones == 0 and tens == 0:
        return digit_zh_table[hectos] + '百'
    return (
        digit_zh_table[hectos] + '百' +
        (digit_zh_table[tens] + '十' if tens != 0 else '零') + 
        (digit_zh_table[ones] if ones != 0 else '')
    )
def num4d_to_zh(num):
    digit_zh_table = '零一二三四五六七八九'
    ones = num % 10
    tens = num // 10 % 10
    hectos = num // 100 % 10
    kilos = num // 1000 % 10
    if kilos == 0:
        return num3d_to_zh(num)
    if ones == 0 and tens == 0 and hectos == 0:
        return digit_zh_table[kilos] + '千'
    if ones == 0 and tens == 0:
        return digit_zh_table[kilos] + '千' + digit_zh_table[hectos] + '百'
    return (
        digit_zh_table[kilos] + '千' +
        (digit_zh_table[hectos] + '百' if hectos != 0 else '零') + 
        (digit_zh_table[tens] + '十' if tens != 0 else '零') + 
        (digit_zh_table[ones] if ones != 0 else '')
    ).replace('零零', '零')


def extreact_pre(md):
    pres = []
    def repl_func(m):
        s = m.group()
        pres.append(s)
        idx = len(pres) - 1
        return f'[PRE{idx}]'
    RE_PRE = r'(`{3,})[\s\S]+?\1'
    md = re.sub(RE_PRE, repl_func, md)
    return md, pres
    
def recover_pre(md, pres):
    for i, pre in enumerate(pres):
        md = md.replace(f'[PRE{i}]', pre)
    return md

def get_md_title(text):
    m = re.search(RE_TITLE, text, flags=re.M)
    if not m:
        return None, (None, None)
    return m.group(1).strip(), m.span(1)
    
def extname(fname):
    m = re.search(r'\.(\w+)$', fname)
    return m.group(1) if m else ''