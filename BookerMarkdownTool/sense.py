from .util import *
from os import path
import zipfile
from io import BytesIO

def filter_sense_file(args):
    print(args.fname)
    ext = extname(arg.fname).lower()
    if ext not in ['md', 'txt']:
        print('请提供 MD 或 TXT 文件')
        return
        
    wdli_fname = path.join(DIR, 'asset', 'TencentSensitiveWords.zip')
    zip = zipfile.ZipFile(BytesIO(open(wdli_fname, 'rb').read()))
    wdli = zip.read('TencentSensitiveWords.txt').decode('utf8', 'ignore').split('\n')
    wdli = [w for w in wdli if w.strip()]
    
    cont = open(args.fname, encoding='utf8').read()
    for w in wdli:
        if w in cont:
            print(f'检测到：{w}')
            nw = '丨'.join(w.split(''))
            cont = cont.replace(w, nw)
            
    open(args.fname, 'w', encoding='utf8').write(cont)
    

            