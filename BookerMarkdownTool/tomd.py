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
from concurrent.futures import ThreadPoolExecutor
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
    
def download_handle(args):
    crawl_cfg['proxy'] = args.proxy
    crawl_cfg['retry'] = args.retry
    html = request_retry(
        'GET', args.url,
        headers=default_hdrs,
        retry=args.retry,
        proxies={'http': args.proxy, 'https': args.proxy},
    ).content.decode(args.encoding, 'ignore')
    
    # 解析标题
    rt = pq(html)
    el_title = rt.find(args.title).eq(0)
    title = el_title.text().strip()
    el_title.remove()
    
    # 判断是否重复
    title_esc = re.sub(r'[^0-9a-zA-Z_\u4e00-\u9fff]', '-', title)
    fname = f'docs/{title_esc}.md'
    if path.isfile(fname):
        print(f'{title} 已存在')
        return
    
    # 解析内容并下载图片
    if args.remove:
        rt('args.remove').remove()
    if args.body:
        co = rt.find(args.body).html()
    else:
        co = Document(str(rt)).summary()
        co = pq(co).find('body').html()
    if not co: 
        print('未获取到内容！')
        return 
    if args.img_src:
        crawl_cfg['imgSrc'] = args.img_src.split(',')
    imgs = {}
    co = process_img(co, imgs, img_prefix='img/', page_url=args.url)
    html = f'''
    <html><body>
    <h1>{title}</h1>
    <blockquote>
    来源：<a href='{args.url}'>{args.url}</a>
    </blockquote>
    {co}</body></html>
    '''
    
    # 转换 md
    md = tomd(html)
    # md = re.sub(RE_CODE_BLOCK, code_replace_func, md)
    yaml_head = '\n'.join([
        '<!--yml',
        'category: ' + args.category,
        'date: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '-->',
    ])
    md = f'{yaml_head}\n\n{md}'
    
    # 写入硬盘
    safe_mkdir('docs')
    safe_mkdir('docs/img')
    open(fname, 'w', encoding='utf-8').write(md)
    for name, data in imgs.items():
        open(f'docs/img/{name}', 'wb').write(data)
        
    print('已完成')

def download_batch_handle(args):
    if not path.isfile(args.fname):
        print('请提供 URL 列表文件')
        return

    urls = open(args.fname, encoding='utf8').read().split('\n')
    urls = [
        u for u in [u.strip() for u in urls] if u
    ]
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    for u in urls:
        args = copy.deepcopy(args)
        args.url = u
        h = pool.submit(download_handle, args)
        hdls.append(h)

    for h in hdls: h.result()
