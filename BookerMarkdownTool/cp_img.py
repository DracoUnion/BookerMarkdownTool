from .util import *
import re
import requests
import hashlib
from os import path
import shutil

def cp_img(args):
    fname = args.fname
    if not fname.endswith('.md'):
        print('请提供 MD 文件')
        return
    
    md = open(fname, encoding='utf8').read()
    img_fnames = [
        path.basename(m.group(1))
        for m in re.finditer(r'!\[[^\]]*\]\(([^\)]+)\)', md)
    ]
    for f in img_fnames:
        fsrc = path.join(args.src, f)
        fdst = path.join(args.dst, f)
        if not path.isfile(fsrc):
            print(f'{fsrc} 不存在！')
            continue
        if path.isfile(fdst):
            os.remove(fdst)
        print(f'{fsrc} -> {fdst}')
        shutil.copy(fsrc, fdst)