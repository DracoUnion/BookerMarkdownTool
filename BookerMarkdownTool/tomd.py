import re
from .util import *
import tempfile
import uuid
import subprocess as subp
import os
import requests
from pyquery import PyQuery as pq
from os import path
from readability import Document
from EpubCrawler.img import process_img
from EpubCrawler.config import config as crawl_cfg
from EpubCrawler.util import request_retry
from datetime import datetime
from multiprocessing import Pool
from .util import *
import copy


RE_IFRAME = r'<iframe[^>]*src="(.+?)"[^>]*>'
RE_IFRAME_ALL = r'</?iframe[^>]*>'
RE_IFRAME_REPL = r'<br/><br/><a href="\1">\1</a><br/><br/>'

# @safe()
def tomd_file(args):
    if not args.fname.endswith('.html'):
        print('请提供 HTML 文件')
        return
    print(args.fname)
    html = open(args.fname, encoding='utf8').read()
    md = tomd(html, args.lang)
    ofname = re.sub(r'\.html$', '', args.fname) + '.md'
    open(ofname, 'w', encoding='utf8').write(md)

def tomd_handle(args):
    if path.isdir(args.fname):
        make_dir_handle(tomd_file)(args)
    else:
        tomd_file(args)


def tomd(html, lang=None):
    # 处理 IFRAME
    html = re.sub(RE_IFRAME, RE_IFRAME_REPL, html)
    html = re.sub(RE_IFRAME_ALL, '', html)
    js_fname = d('tomd.js')
    html_fname = path.join(tempfile.gettempdir(), uuid.uuid4().hex + '.html')
    open(html_fname, 'w', encoding='utf8').write(html)
    subp.Popen(
        ["node", js_fname, html_fname],
        shell=True,
    ).communicate()
    md_fname = re.sub(r'\.html$', '', html_fname) + '.md'
    md = open(md_fname, encoding='utf8').read()
    os.remove(html_fname)
    if lang:
        md = re.sub(r'```([\s\S]+?```)', '```' + lang + r'\1', md)
    return md
  