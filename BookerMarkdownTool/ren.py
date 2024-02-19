import os
from os import path
import copy
from multiprocessing import Pool
import re
from  urllib.parse import urlparse
import shutil

RE_TITLE = r'^#+ (.+?)$'
RE_SOURCE = r'原文：<(.+?)>'
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
    nfname = re.sub(r'\s', '-', fname_escape(title)) + '.md'
    nfname = path.join(path.dirname(fname), nfname)
    print(f'{fname} => {nfname}')
    shutil.move(fname, nfname)
