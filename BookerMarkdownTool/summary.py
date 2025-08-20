import os
from os import path
import re
from collections import OrderedDict
import yaml
import traceback
from urllib.parse import quote_plus
from .util import *

RE_YAML_META = r'<!--yml([\s\S]+?)-->'

def docs_summary_handle(args):
    dir = args.dir
    doc_dir = path.join(dir, 'docs')
    if not path.isdir(doc_dir):
        print('请提供文档目录')
        return
    doc_names = [
        d for d in os.listdir(doc_dir)
        if path.isdir(path.join(doc_dir, d)) and
           path.isfile(path.join(doc_dir,d, 'README.md'))
    ]
    toc = []
    for d in doc_names:
        readme_fname = path.join(doc_dir, d, 'README.md')
        readme = open(
            readme_fname,
            encoding='utf8',
            errors='ignore',
        ).read()
        title, _ = get_md_title(readme)
        if not title: continue
        toc.append(f'+   [{title}](docs/{d}/README.md)')
        summary_fname = path.join(doc_dir, d, 'SUMMARY.md')
        if args.all and path.isfile(summary_fname):
            summary = open(
                summary_fname,
                encoding='utf8',
                errors='ignore',
            ).read().strip()
            summary = re.sub(r'^', 'x20' * 4, summary, re.M)
            toc.append(summary)


    summary = '\n'.join(toc)
    open(path.join(dir, 'SUMMARY.md'), 'w', encoding='utf8').write(summary)


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
        cont = open(
            fullf, 
            encoding='utf8',
            errors='ignore',
        ).read()
        title, _ = get_md_title(cont)
        if not title: continue
        toc.append(f'+   [{title}]({f})')
    summary = '\n'.join(toc)
    open(path.join(dir, 'SUMMARY.md'), 'w', encoding='utf8').write(summary)
    
def ext_meta(md):
    m = re.search(RE_YAML_META, md)
    if not m: 
        return {
            'date': '0001-01-01 00:00:00',
            'cate': '未分类',
            'title': get_md_title(md)[0]
        }
    try:
        meta = yaml.safe_load(m.group(1))
    except Exception as ex: 
        return {
            'date': '0001-01-01 00:00:00',
            'cate': '未分类',
            'title': get_md_title(md)[0]
        }
    return {
        'date': meta.get('date', '0001-01-01 00:00:00'),
        'cate': meta.get('category', '未分类'),
        'title': get_md_title(md)[0]
    }


def wiki_summary_handle(args):
    # 读入文件列表
    fnames = [f for f in os.listdir('docs') if f.endswith('.md')]
    toc = OrderedDict()
    for fname in fnames:
        print(fname)
        md = open(
            path.join('docs', fname), 
            encoding='utf8',
            errors='ignore',
        ).read()
        # 提取元信息
        meta = ext_meta(md)
        if not meta['title']:
            print('未找到标题，已跳过')
            continue
        cate = meta['cate']
        toc.setdefault(cate, [])
        toc[cate].append({
            'title': meta['title'],
            'file': fname,
            'date': meta['date'],
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
