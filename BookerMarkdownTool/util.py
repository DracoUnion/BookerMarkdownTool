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
import hashlib
from functools import reduce
from urllib.parse import quote_plus
from os import path
from pyquery import PyQuery as pq
from datetime import datetime
from collections import OrderedDict
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
from typing import *
import imgyaso
from pydantic import BaseModel, parse_obj_as, ValidationError

DIR = path.dirname(path.abspath(__file__))

default_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
}

headers = {
    'User-Agent': 'PostmanRuntime/7.26.8',
    'Referer': 'https://www.bilibili.com/',
}

RE_TITLE = r'^#+\x20+(.+?)$'

def d(name):
    return path.join(DIR, name)

def asset(name=''):
    return path.join(DIR, 'assets', name)

def md2html_pandoc(md):
    fname = path.join(tempfile.gettempdir(), uuid.uuid4().hex + '.md')
    ofname = fname[:-3] + '.html'
    open(fname, 'w', encoding='utf8').write(md)
    subp.Popen(['pandoc', fname, '-o', ofname]).communicate()
    html = open(ofname, encoding='utf8').read()
    safe_remove(fname)
    safe_remove(ofname)
    return html

def safe_remove(fname):
    try: os.unlink(fname)
    except: pass

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
            except KeyboardInterrupt:
                raise
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
        except KeyboardInterrupt:
            raise
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

def get_md_credit(text):
    RE_CREDIT = r'^>\x20(?:原文|来源|链接|译者|协议)：.*$'
    credits = re.findall(RE_CREDIT, text, flags=re.M)
    return '\n> \n'.join(credits)

def rm_xml_header(html):
    html = re.sub(r'<\?xml[^>]*\?>', '', html)
    html = re.sub(r'xmlns(:\w+)?=".+?"', '', html)
    html = re.sub(r'</?\w+', lambda m: m.group().lower(), html)
    return html


def group_chunks(chunks, limit=8000):
    groups = ['']
    for c in chunks:
        if len(groups[-1]) +  len(c) + 2 > limit:
            groups.append(c)
        else:
            groups[-1] += '\n\n' + c
    groups = [g for g in groups if g]
    return groups

def split_md_lines(md):
    lines = md.split('\n')
    res = []
    in_code = False
    code = ''
    for l in lines:
        if '```' in l:
            if in_code: 
                # 结尾
                code += l
                res.append(code)
                code = ''
            else:
                # 开头
                code += l + '\n'
            in_code = not in_code
        elif not in_code:
            if l.strip(): res.append(l)
        elif in_code:
            code += l + '\n'
    # 处理结尾缺失情况：
    if code:
        res.append(code + '```')
    return res

def md5(text: str):
    return hashlib.md5(text.encode('utf8')).hexdigest()


def gen_objs_md5(*args):
    args = [
        o if isinstance(o, str) else
            json_dump_model(o)
        for o in args
    ]
    return '_'.join(md5(o) for o in args)


def render_prompt(prompt: str, **kw):
    return re.sub(r"{(\w+)}", lambda g: kw.get(g.group(1), g.group(0)), prompt)


def tok_en_zh(text):
    return re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', text)


def get_ngram_set(toks, n):
    return set(tuple(toks[i:i+n]) for i in range(len(toks)-n+1))


def ngram_jaccard(text1: str, text2: str, n: int = 3) -> float:
    set1 = get_ngram_set(tok_en_zh(text1.lower()), n)
    set2 = get_ngram_set(tok_en_zh(text2.lower()), n)
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union if union else 0.0


def ngram_coverage(src: str, gen: str, n: int = 3) -> float:
    src_set = get_ngram_set(tok_en_zh(src.lower()), n)
    gen_set = get_ngram_set(tok_en_zh(gen.lower()), n)
    inter = len(src_set & gen_set)
    all_ = len(gen_set)
    return inter / all_ if all_ else 0.0


def ext_code_block(s):
    return re.search(r'```\w*([\s\S]+)```', s).group(1)


def ext_cont_block(s):
    return re.search(r'\[content\]([\s\S]+)\[/content\]', s).group(1)


def json_dump_model(obj) -> str:
    """将对象（含 pydantic 模型/列表）序列化为 JSON 字符串。"""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump()
    elif isinstance(obj, list):
        obj = [
            it.dict() if isinstance(it, BaseModel) else it
            for it in obj
        ]
    return json.dumps(obj, ensure_ascii=False)


def json_load_model(text: str, model: Type[BaseModel]):
    """将 JSON 文本解析为指定 pydantic 模型。"""
    try:
        return parse_obj_as(model, json.loads(text))
    except json.JSONDecodeError:
        return None
    except ValidationError:
        return None


def write_text(fname: str, text: str, append: bool = False) -> None:
    """将 text 以 UTF-8 写入 fname（自动创建父目录）。"""
    os.makedirs(path.dirname(fname), exist_ok=True)
    open(fname, 'a' if append else 'w', encoding='utf8').write(text)


def read_text(fname: str) -> str:
    """以 UTF-8 读取 fname 的文本内容。"""
    if not path.isfile(fname):
        return None
    text = open(fname, encoding='utf8').read()
    chs = set(text)
    # 避免读取损坏的数据
    if len(chs) == 1 and '\x00' in chs:
        text = ""
    return text


def write_yaml_model(fname: str, obj: Any) -> None:
    """将对象（含 pydantic 模型/列表）以 YAML 形式写入 fname。"""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump()
    elif isinstance(obj, list):
        obj = [
            it.model_dump() if isinstance(it, BaseModel) else it
            for it in obj
        ]
    os.makedirs(path.dirname(fname), exist_ok=True)
    with open(fname, 'w', encoding='utf8') as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


def read_yaml_model(fname: str, model: Optional[Type[BaseModel]]):
    """从 fname 读取 YAML 并解析为指定 pydantic 模型；文件缺失或损坏时返回 None。"""
    if not path.isfile(fname) or not path.getsize(fname):
        return None
    try:
        data = yaml.safe_load(open(fname, encoding='utf8').read())
        return parse_obj_as(model, data) if model else data
    except yaml.YAMLError:
        return None
    except ValidationError:
        return None


def repl_code_block(md: str) -> Tuple[str, List[str]]:
    blocks = []
    def repl_func(g):
        s = g.group()
        tk = f'[PRE{len(blocks)}]'
        blocks.append(s)
        return tk
    CODE_BLOCK_RE = r'''
        # 代码块
        ```[\s\S]+?```
        |
        # 图片
        !\[.*?\]\(.+?\)
        |
        # 公式块
        \$\$[\s\S]+?\$\$
    '''
    md = re.sub(CODE_BLOCK_RE, repl_func, md, flags=re.VERBOSE)
    return md, blocks


def rec_code_block(md: str, blocks: List[str]) -> str:
    for i, b in enumerate(blocks):
        md = md.replace(f'[PRE{i}]', b)
    return md
