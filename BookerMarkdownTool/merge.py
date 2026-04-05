import os
from os import path
from .util import *
from .chunker import chunk_markdown

def merge(args):
    dir = path.abspath(args.dir)
    if not path.isdir(dir):
        print('请提供目录')
        return
    fnames = [
        path.join(base, f) 
        for base, _, fnames in os.walk(dir) 
        for f in fnames 
        if f.endswith('.md')
    ]
    # 过滤 README SUMMARY
    fnames = [
        f for f in fnames
        if path.basename(f) not in ['README.md', 'SUMMARY.md']
    ]
    
    mds = [
        open(f, encoding='utf8', errors='ignore').read() 
        for f in fnames
    ]

    md = '\n\n'.join(mds)
    cres = chunk_markdown(md, path.basename(dir))
    chunks = [c.content for c in cres.chunks]
    groups = ['']
    for c in chunks:
        if groups[-1].count('\n') < args.lines:
            groups[-1] += '\n\n' + c
        else:
            groups.append(c)
            
    groups = [g for g in groups if g]

    # 批量替换图像前缀
    if args.img_pref:
        if not args.img_pref.endswith('/'):
            args.img_pref += '/'
        groups = [
            re.sub(r'(?<=\]\()img/', args.img_pref, g)
            for g in groups
        ]

    # 未设置标题情况下从 README 里面读取标题并设置
    credit = ''
    if  not args.title and \
        path.isfile(path.join(args.dir, 'README.md')):
        readme = open(path.join(args.dir, 'README.md'), encoding='utf8').read()
        args.title, _ = get_md_title(readme)
        credit = get_md_credit(readme)

    l = len(str(len(groups)))
    for i, g in enumerate(groups):
        fname = dir + '-merge-' + str(i).zfill(l) + '.md'
        print(fname)
        title = f'# {args.title}（{num4d_to_zh(i + 1)}）'
        g = f'{title}\n\n{credit}\n\n{g}'
        open(fname, 'w', encoding='utf8').write(g)
    
            