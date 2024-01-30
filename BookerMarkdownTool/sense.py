from .util import *
from os import path
import zipfile
from io import BytesIO
import re

def filter_sense_file(args):
    print(args.fname)
    ext = extname(args.fname).lower()
    if ext not in ['md', 'txt']:
        print('请提供 MD 或 TXT 文件')
        return
        
    wdli_fname = path.join(DIR, 'asset', 'TencentSensitiveWords.zip')
    zip = zipfile.ZipFile(BytesIO(open(wdli_fname, 'rb').read()))
    wdli = zip.read('TencentSensitiveWords.txt').decode('utf8', 'ignore').split('\n')
    wdli = [w for w in wdli if w.strip()]
    
    cont = open(args.fname, encoding='utf8').read()
    for w in wdli:
        if len(w) == 1: continue
        if re.search(r'^[\x20-\x7f]+$', w): continue
        if w in cont:
            print(f'检测到：{w}')
            nw = '丨'.join([ch for ch in w])
            cont = cont.replace(w, nw)
            
    open(args.fname, 'w', encoding='utf8').write(cont)
    

            