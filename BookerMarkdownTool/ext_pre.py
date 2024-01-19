import re
from os import path
import json
import os
from .util import *
    
def extract_pre_handler(args):
    if path.isdir(args.fname):
        make_dir_handle(extract_pre_file)(args)
    else:
        extract_pre_file(args)
    
def extract_pre_file(args):
    fname = args.fname
    if not fname.endswith('.md'):
        print('请提供MD文件')
        return
    json_fname = fname + '.json'
    if path.isfile(json_fname):
        print('文件中的代码段已提取')
        return
    md = open(fname, encoding='utf8').read()
    md, pres = extreact_pre(md)
    open(fname, 'w', encoding='utf8').write(md)
    open(json_fname, 'w', encoding='utf8').write(json.dumps(pres))
    
def recover_pre_handler(args):
    if path.isdir(args.fname):
        make_dir_handle(recover_pre_file)(args)
    else:
        recover_pre_file(args)

def recover_pre_file(args):
    fname = args.fname
    if not fname.endswith('.md'):
        print('请提供MD文件')
        return
    json_fname = fname + '.json'
    if not path.isfile(json_fname):
        print('找不到已提取的代码段')
        return
    md = open(fname, encoding='utf8').read()
    pres = json.loads(open(json_fname, encoding='utf8').read())
    md = recover_pre(md, pres)
    open(fname, 'w', encoding='utf8').write(md)
    os.unlink(json_fname)
