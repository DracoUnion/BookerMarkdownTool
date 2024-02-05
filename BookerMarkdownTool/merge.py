import os
from os import path
from .util import *

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
    
    mds = [open(f, encoding='utf8').read() for f in fnames]
    for i in range(0, len(mds) - 1):
        if mds[i].count('\n') < args.lines:
            mds[i+1] = mds[i] + '\n\n' + mds[i+1]
            mds[i] = ''
            
    mds = [md for md in mds if md]

    # 批量替换图像前缀
    if args.img_pref:
        if not args.img_pref.endswith('/'):
            args.img_pref += '/'
        mds = [
            re.sub(r'(?<=\]\()img/', args.img_pref, md)
            for md in mds
        ]

    # 未设置标题情况下从 README 里面读取标题并设置
    credit = ''
    if  not args.title and \
        path.isfile(path.join(args.dir, 'README.md')):
        readme = open(path.join(args.dir, 'README.md'), encoding='utf8').read()
        args.title, _ = get_md_title(readme)
        credit = get_md_credit(readme)

    l = len(str(len(mds)))
    for i, md in enumerate(mds):
        fname = dir + '-merge-' + str(i).zfill(l) + '.md'
        print(fname)
        title = f'# {args.title}（{num4d_to_zh(i + 1)}）'
        md = f'{title}\n\n{credit}\n\n{md}'
        open(fname, 'w', encoding='utf8').write(md)
    
            