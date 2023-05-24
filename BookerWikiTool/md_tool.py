from os import path
import os
import re
from .util import *

def config_proj(args):
    dir = path.abspath(args.dir)
    if not path.isdir(dir):
        print('请提供目录')
        return
    fnames = os.listdir(dir)
    if 'README.md' not in fnames or \
        'index.html' not in fnames or \
        'CNAME' not in fnames:
        print('缺少 README.md，index.html 或 CNAME 文件')
        return
    name = input('请输入中文名称：').strip() or '{name}'
    name_en = input('请输入英文名称：').strip() or '{nameEn}'
    url_en = input('请输入英文链接：').strip() or '{urlEn}'
    domain = input('请输入域名前缀：').strip() or '{domain}'
    color = input('请输入颜色：').strip() or '{color}'
    repo = path.basename(dir)
    
    conts = {
        'README.md': open(path.join(dir, 'README.md'), encoding='utf8').read(),
        'index.html': open(path.join(dir, 'index.html'), encoding='utf8').read(),
        'CNAME': open(path.join(dir, 'CNAME'), encoding='utf8').read(),
    }
    for fname, cont in conts.items():
        cont = (
            cont.replace('{name}', name)
                .replace('{nameEn}', name_en)
                .replace('{urlEn}', url_en)
                .replace('{urlEn}', url_en)
                .replace('{domain}', domain)
                .replace('{color}', color)
                .replace('{adminName}', '飞龙')
                .replace('{adminUn}', 'wizardforcel')
                .replace('{adminQq}', '562826179')
                .replace('{repo}', repo)
                .replace('{dockerName}', repo)
                .replace('{pypiName}', repo)
                .replace('{npmName}', repo)
        )
        open(path.join(dir, fname), 'w', encoding='utf8').write(cont)

def convert_cdrive_log(args):
    RE_INFO = r'\[(.+?)\]([^\[]+)'
    RE_TITLE = r'上传: (.+?) \([\d\.]+ \w+\)\n'
    RE_META = r'META URL -> (\S+)'
    
    fname = args.fname
    co = open(fname, encoding='utf8').read()
    cos = co.split(' 上传: ')
    res = ['| 文件 | 链接 |\n| --- | --- |\n']
    for info in cos:
        info = ' 上传: ' + info
        title = re.search(RE_TITLE, info)
        meta = re.search(RE_META, info)
        if not title: continue
        title = title.group(1)
        meta = meta.group(1) if meta else '未上传'
        res.append(f'| {title} | {meta} |\n')
        
    res = ''.join(res)
    open(fname + '.md', 'w', encoding='utf8').write(res)
