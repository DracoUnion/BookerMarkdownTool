import os
from os import path
import re
from collections import OrderedDict
import yaml
import traceback
from urllib.parse import quote_plus
from .util import *

RE_YAML_META = r'<!--yml([\s\S]+?)-->'


def summary_handle(args):
    # 读入文件列表
    dir = args.dir
    fnames = [f for f in os.listdir(dir) if f.endswith('.md')]
    if 'README.md' in fnames:
        idx = fnames.index('README.md')
        del fnames[idx]
        fnames.insert(0, 'README.md')
    toc = []
    for f in fnames:
        fullf = path.join(dir, f)
        print(fullf)
        cont = open(fullf, encoding='utf8').read()
        title, _ = get_md_title(cont)
        if not title: continue
        toc.append(f'+   [{title}]({f})')
    summary = '\n'.join(toc)
    open(path.join(dir, 'SUMMARY.md'), 'w', encoding='utf8').write(summary)
    
def wiki_summary_handle(args):
    # 读入文件列表
    fnames = [f for f in os.listdir('docs') if f.endswith('.md')]
    toc = OrderedDict()
    for fname in fnames:
        print(fname)
        md = open(path.join('docs', fname), encoding='utf8').read()
        # 提取元信息
        m = re.search(RE_YAML_META, md)
        if not m: 
            print('未找到元信息，已跳过')
            continue
        try:
            meta = yaml.safe_load(m.group(1))
        except Exception as ex: 
            traceback.print_exc()
            continue
        dt = meta.get('date', '0001-01-01 00:00:00')
        cate = meta.get('category', '未分类')
        # 提取标题
        title, _ = get_md_title(md)
        if not title: 
            print('未找到标题，已跳过')
            continue
        toc.setdefault(cate, [])
        toc[cate].append({
            'title': title,
            'file': fname,
            'date': dt,
        })
    
    # 生成目录文件
    summary = ''
    for cate, sub in toc.items():
        summary += f'+   {cate}\n'
        for art in sub:
            title = art['title']
            file = quote_plus(art['file'])
            summary += f'    +   [{title}](docs/{file})\n'
    open('SUMMARY.md', 'w', encoding='utf8').write(summary)
