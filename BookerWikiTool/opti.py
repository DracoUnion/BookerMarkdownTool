import re
from os import path
import copy
from multiprocessing import Pool

# @safe()
def opti_md_file(args):
    RE_SRC_FULL = r'原文[:：]\[.+?\]\((.+?)\)'
    RE_SRC_FULL_REP = r'原文：<\1>'
    RE_PRE_HEAD = r'^\x20*\*+\x20*```'
    RE_LEG_TOKEN = r'T\d+】'
    RE_PRE_HEAD2 = r'```\*+|\*+```'
    fname = args.fname
    if not fname.endswith('.md'):
        print('请提供 Markdown 文件')
        return
    print(fname)
    cont = open(fname, encoding='utf8').read()
    cont = cont.replace('../Images/', 'img/')
    cont = re.sub(RE_LEG_TOKEN, '', cont)
    cont = re.sub(RE_SRC_FULL, RE_SRC_FULL_REP, cont)
    cont = re.sub(r'#\d+\-\d+\-\d+(?=>)', '', cont)
    cont = re.sub(RE_PRE_HEAD, '```', cont, flags=re.M)
    cont = re.sub(RE_PRE_HEAD2, '```', cont)
    open(fname, 'w', encoding='utf8').write(cont)
   


def opti_md_handle(args):
    if path.isdir(args.fname):
        opti_md_dir(args)
    else:
        opti_md_file(args)

def opti_md_dir(args):
    dir = args.fname
    fnames = os.listdir(dir)
    pool = Pool(args.threads)
    for fname in fnames:
        args = copy.deepcopy(args)
        args.fname = path.join(dir, fname)
        # tomd_file(args)
        pool.apply_async(opti_md_file, [args])
    pool.close()
    pool.join()