import pyturndown
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

# 规则字典
RULES = {}


def register_rule(name, filter_condition, replacement_func):
    """
    注册一个转换规则。

    Args:
        name: 规则名称
        filter_condition: 匹配条件（字符串、列表或函数）
        replacement_func: 转换函数
    """
    RULES[name] = {
        'filter': filter_condition,
        'replacement': replacement_func
    }


# 上标字符映射表（0-9）
SUPERSCRIPTS = {str(i):it for i, it in enumerate('⁰¹²³⁴⁵⁶⁷⁸⁹')}

# ---------- filter 函数（均为独立 def） ----------
def filter_math(node, options):
    return node.tag == 'math'


def filter_p_in_td(node, options):
    return (node.tag == 'p' and
            node.getparent() is not None and
            node.getparent().tag in ('td', 'th'))

def filter_caption(node, options):
    return node.tag in (
        'figcaption', 'caption'
    )


def filter_span_div(node, options):
    return node.tag in (
        'span', 'div', 'article', 'section', 'header', 'footer',
        'figure', 'nav', 'u', 'center', 'small', 'cite', 'mark',
        'font', 'big', 'time', 'address', 'abbr', 'object'
    )

def filter_clean(node, options):
    return node.tag in (
        'style', 'base', 'meta', 'script', 'ins', 'aside',
        'noscript', 'form', 'label', 'input', 'button',
        'col', 'colgroup', 'title',
    )

def filter_a_no_href(node, options):
    return node.tag == 'a' and not node.get('href')

def filter_single_pre(node, options):
    if node.tag not in ('pre', 'textarea'):
        return False
    children = node.getchildren()
    has_code = len(children) == 1 and children[0].tag == 'code'
    return not has_code

def filter_in_pre(node, options):
    parent = node.getparent()
    return parent is not None and parent.tag == 'pre' and node.tag != 'br'

def filter_media(node, options):
    return node.tag in (
        'iframe', 'video', 'audio', 'source'
    )

def filter_sub(node, options):
    return node.tag == 'sub'

def filter_sup(node, options):
    return node.tag == 'sup'

# ---------- replacement 函数（均为独立 def） ----------
def repl_math(content, node, options):
    tex = node.get('alttext')
    if tex:
        return '$' + tex.strip() + '$'
    return content

def repl_p_in_td(content, node, options):
    return content

def repl_caption(content, node, options):
    return '\n\n' + content + '\n\n'

def repl_dl(content, node, options):
    return content

def repl_span_div(content, node, options):
    return content

def repl_clean(content, node, options):
    return ''

def repl_a_no_href(content, node, options):
    return content

def repl_single_pre(content, node, options):
    # 注意：此规则标记为 leaf，因此 content 实际上是 node.text_content()
    return '\n\n```\n' + content + '\n```\n\n'

def repl_in_pre(content, node, options):
    return content

def repl_media(content, node, options):
    src = node.get('src')
    prefix = '\n\n<' + src + '>\n\n' if src else ''
    return prefix + content

def repl_sub(content, node, options):
    return '[' + content + ']'

def repl_sup(content, node, options):
    # 如果内容为单个数字（0-9），返回上标字符
    if content in SUPERSCRIPTS:  # 直接匹配字符
        return SUPERSCRIPTS[content]
    # 如果长度1，返回 ^x
    if len(content) == 1:
        return '^' + content
    # 否则返回 ^(xxx)
    return '^(' + content + ')'

register_rule('a_no_href', filter_a_no_href, repl_a_no_href)
register_rule('clean', filter_clean, repl_clean)
register_rule('in_pre', filter_in_pre, repl_in_pre)
register_rule('math', filter_math, repl_math)
register_rule('media', filter_media, repl_media)
register_rule('p_in_td', filter_p_in_td, repl_p_in_td)
register_rule('single_pre', filter_single_pre, repl_single_pre)
register_rule('span_div', filter_span_div, repl_span_div)
register_rule('sub', filter_sub, repl_sub)
register_rule('sup', filter_sup, repl_sup)
register_rule('caption', filter_caption, repl_caption)

# 导出规则字典
def get_rules():
    """
    获取所有 GFM 规则的字典。

    Returns:
        dict: 规则名称到规则字典的映射
    """
    return RULES.copy()

def tomd(html, lang=None):
    # 处理 IFRAME
    RE_IFRAME = r'<iframe[^>]*src="(.+?)"[^>]*>'
    RE_IFRAME_ALL = r'</?iframe[^>]*>'
    RE_IFRAME_REPL = r'<br/><br/><a href="\1">\1</a><br/><br/>'
    html = re.sub(RE_IFRAME, RE_IFRAME_REPL, html)
    html = re.sub(RE_IFRAME_ALL, '', html)
    tds = pyturndown.TurndownService()
    for k, r in get_rules().items():
        tds.add_rule(k, r)
    md = tds.turndown(html)
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


def reg_subparser(subparsers):
    dl_parser = subparsers.add_parser("download", help="download a page")
    dl_parser.add_argument("url", help="url")
    dl_parser.add_argument("-e", "--encoding", default='utf-8', help="encoding")
    dl_parser.add_argument("-c", "--category", default='未分类', help="category")
    dl_parser.add_argument("-t", "--title", default='title', help="selector of article title")
    dl_parser.add_argument("-b", "--body", default='', help="selector of article body")
    dl_parser.add_argument("-r", "--remove", default='', help="selector of elements to remove")
    dl_parser.add_argument("-i", "--img-src", default='', help="prop names of <img> holding src")
    dl_parser.add_argument("-p", "--proxy", help="proxy")
    dl_parser.add_argument("--retry", type=int, default=3, help="num for retry")
    dl_parser.set_defaults(func=download_handle)

    dl_batch_parser = subparsers.add_parser("download-batch", help="download pages")
    dl_batch_parser.add_argument("fname", help="url file name")
    dl_batch_parser.add_argument("-e", "--encoding", default='utf-8', help="encoding")
    dl_batch_parser.add_argument("-c", "--category", default='未分类', help="category")
    dl_batch_parser.add_argument("-t", "--title", default='title', help="selector of article title")
    dl_batch_parser.add_argument("-b", "--body", default='', help="selector of article body")
    dl_batch_parser.add_argument("-r", "--remove", default='', help="selector of elements to remove")
    dl_batch_parser.add_argument("-i", "--img-src", default='', help="prop names of <img> holding src")
    dl_batch_parser.add_argument("-p", "--proxy", help="proxy")
    dl_batch_parser.add_argument("--threads", type=int, default=8, help="threads num")
    dl_batch_parser.add_argument("--retry", type=int, default=3, help="num for retry")
    dl_batch_parser.set_defaults(func=download_batch_handle)

    tomd_parser = subparsers.add_parser("tomd", help="html to markdown")
    tomd_parser.add_argument("fname", help="file or dir name")
    tomd_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    tomd_parser.add_argument("-l", "--lang", help="code language")
    tomd_parser.set_defaults(func=tomd_handle)

