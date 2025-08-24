from util import *
import re
import requests
import hashlib

def dl_img_handle(args):
    fname = args.fname
    if not fname.endswith('.md'):
        raise ValueError('请提供 Makrdown')
    img_dir = path.join(path.dirname(fname), 'img')
    safe_mkdir(img_dir)
    md = open(fname, encoding='utf8').read()
    mts = list(re.finditer(r'\[[^\]]*\]\(([^\)]+)\)', md))
    for m in mts:
        url = m.group(1)
        if not url.startswith('http'): continue
        print(url)
        hash_ = hashlib.md5(url.encode('utf8')).hexdigest()
        data = requests.get(url).content
        img_fname = path.join(
            path.dirname(fname, 'img',  f'{hash_}.png'))
        open(img_fname, 'wb').write(data)
        md = md.replace(url, f'img/{hash_}.png')

    open(fname, 'w', encoding='utf8').write(md)
