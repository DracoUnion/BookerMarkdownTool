import os
from os import path
import copy
from multiprocessing import Pool
import re
from  urllib.parse import urlparse
import shutil
from .util import *

RE_TITLE = r'^#+ (.+?)$'
RE_SOURCE = r'原文：.*?(https?://[\w\-\./\+%\?=&#]+)'
RE_SRC_TITLE = r'[\w\-]{15,}'


def ren_md_handle(args):
    if path.isdir(args.fname):
        ren_md_dir(args)
    else:
        ren_md_file(args)

def ren_md_dir(args):
    dir = args.fname
    fnames = os.listdir(dir)
    pool = Pool(args.threads)
    for f in fnames:
        args = copy.deepcopy(args)
        args.fname = path.join(dir, f)
        pool.apply_async(ren_md_file, [args])
    pool.close()
    pool.join()

# @safe()

def get_md_title(md):
    rm = re.search(RE_TITLE, md, flags=re.M)
    if not rm: return
    return rm.group(1)
    
def get_md_src_title(cont):
    rm = re.search(RE_SOURCE, cont, flags=re.M)
    if not rm: return
    src = rm.group(1)
    p = urlparse(src).path
    rm = re.search(RE_SRC_TITLE, p)
    if not rm: return
    return rm.group()

def ren_md_file(args):
    fname = args.fname
    if not fname.endswith('.md'):
        print('请提供 markdown 文件')
        return
    cont = open(fname, encoding='utf8').read()
    title = get_md_src_title(cont) \
        if args.by == 'src' else get_md_title(cont)
    if not title:
        print(f"未找到 {fname} 的标题")
        return
    nfname = re.sub(r'[^0-9a-zA-Z_\u4e00-\u9fff]', '-', title) + '.md'
    nfname = path.join(path.dirname(fname), nfname)
    print(f'{fname} => {nfname}')
    shutil.move(fname, nfname)


def reg_subparser(subparsers):
    ren_parser = subparsers.add_parser("ren-md", help="rename md fname")
    ren_parser.add_argument("fname", help="file for dir name")
    ren_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    ren_parser.add_argument("-b", "--by", type=str, choices=['title', 'src'], default='src', help="where to extract fname")
    ren_parser.set_defaults(func=ren_md_handle)
