from .util import *
import re
import requests
import hashlib
from os import path
import shutil
from concurrent.futures import ThreadPoolExecutor

def tr_cp_file(fsrc, fdst):
    if not path.isfile(fsrc):
        print(f'{fsrc} 不存在！')
        return
    if path.isfile(fdst):
        os.remove(fdst)
    print(f'{fsrc} -> {fdst}')
    shutil.copy(fsrc, fdst)

def cp_img(args):
    if not path.isdir(args.src):
        print('来源目录不存在')
        return
    os.makedirs(args.dst, exist_ok=True)
    fnames = [args.fname] if path.isfile(args.fname) else \
             [path.join(args.fname, f) for f in os.listdir(args.fname)]
    fnames = [f for f in fnames if f.endswith('.md')]
    if not fnames:
        print('请提供 MD 文件或目录')
        return

    pool = ThreadPoolExecutor(args.file_threads)
    hdls = []
    for f in fnames:
        args = copy.deepcopy(args)
        args.fname = f
        h = pool.submit(cp_img_file, args)
        hdls.append(h)
    for h in hdls:
        h.result()

def cp_img_file(args):
    fname = args.fname
    if not fname.endswith('.md'):
        print('请提供 MD 文件')
        return
    
    print(fname)
    md = open(fname, encoding='utf8').read()
    img_fnames = [
        path.basename(m.group(1))
        for m in re.finditer(r'!\[[^\]]*\]\(([^\)]+)\)', md)
    ]
    pool = ThreadPoolExecutor(args.img_threads)
    hdls = []
    for f in img_fnames:
        fsrc = path.join(args.src, f)
        fdst = path.join(args.dst, f)
        h = pool.submit(tr_cp_file, fsrc, fdst)
        hdls.append(h)
    for h in hdls:
        h.result()

def reg_subparser(subparsers):
    copy_parser = subparsers.add_parser("cp-img", help="copy imgs in mds")
    copy_parser.add_argument("fname", help="fname")
    copy_parser.add_argument("src", help="source dir")
    copy_parser.add_argument("dst", help="dest dir (auto create)")
    copy_parser.add_argument("-it", "--img-threads", type=int, default=16, help="img threads")
    copy_parser.add_argument("-ft", "--file-threads", type=int, default=4, help="file threads")
    copy_parser.set_defaults(func=cp_img)