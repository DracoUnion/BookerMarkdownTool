import os
from os import path

def merge(args):
    dir = path.abspath(args.dir)
    if not path.isdir(dir):
        print('请提供目录')
        return
    fnames = [path.join(base, f) for base, _, fnames in os.walk(dir) for f in fnames if f.endswith('.md')]
    
    mds = [open(f, encoding='utf8').read() for f in fnames]
    for i in range(0, len(mds) - 1):
        if mds[i].count('\n') < args.lines:
            mds[i+1] = mds[i] + '\n\n' + mds[i+1]
            mds[i] = ''
            
    mds = [md for md in mds if md]
    
    l = len(str(len(mds)))
    for i, md in enumerate(mds):
        fname = dir + '-' + str(i).zfill(l) + '.md'
        print(fname)
        title = f'{args.title} {i}'
        md = f'# {title}\n\n{md}'
        open(fname, 'w', encoding='utf8').write(md)
    
            