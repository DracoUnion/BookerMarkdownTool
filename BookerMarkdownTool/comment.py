import os
import subprocess as subp
from os import path
import re
from .util import *
import shlex

CODE_COMMENT_PROMPT = '请给以下代码的每一行添加注释，输出注释后的代码：'

def group_lines(lines, limit):
    res = ['']
    for l in lines:
        if len(res[-1]) + len(l) + 1 > limit:
            res.append([l])
        else:
            res[-1] += '\n' + l
    return res
        
def glmcpp_code_comment(code, args):
    code = code.replace('\n', '\\n')
    cmd = ['chatglm', '-p', args.prompt + code, '-m', args.model]
    print(f'cmd: {cmd}')
    r = subp.Popen(
            cmd, stdout=subp.PIPE, stderr=subp.PIPE, shell=True
    ).communicate()
    if r[1]:
        errmsg = r[1].decode('utf8')
        raise Exception(errmsg)
    text = r[0].decode('utf8')
    print(text)
    return text

def code_comment_handle(args):
    glm_path = find_cmd_path('chatglm')
    if not glm_path:
        print('请下载 chatglm.cpp 并将目录添加到 $PATH 中')
        return
    if re.search(r'^[\w\-]+$', args.model):
        args.model = path.join(glm_path, 'models', args.model + '.bin')

    if path.isdir(args.fname):
        code_comment_dir(args)
    else:
        code_comment_file(args)

def code_comment_dir(args):
    dir = args.fname
    for d, _, fnames in os.walk(dir):
        for f in fnames:
            ff = path.join(d, f)
            args.fname = ff
            code_comment_file(args)

def code_comment_file(args):
    fname = args.fname
    print(fname)
    lines = open(fname, encoding='utf8').read().split('\n')
    chunks = group_lines(lines, args.limit)
    res = '\n'.join([glmcpp_code_comment(c, args) for c in chunks])
    res = re.sub(r'^```\w*$', '', res)
    md = f'#\x20`{fname}`代码注释\n\n```\n{res}\n```'
    ofname = fname + '.md'
    open(ofname, 'w', encoding='utf8').write(md)
