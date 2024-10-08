import re
from os import path
import yaml
import json
import os
from .util import *

PREF_IND = r'(\x20{4}|\t)'
PREF_OL = r'\d+\.\x20{2}'
PREF_UL = r'[\*\+\-]\x20{3}'
PREF_H1 = r'#\x20+'
PREF_H2 = r'#{2}\x20+'
PREF_H3 = r'#{3}\x20+'
PREF_H4 = r'#{4}\x20+'
PREF_H5 = r'#{5}\x20+'
PREF_H6 = r'#{6}\x20+'
PREF_BQ = r'>\x20'
TYPE_TB = r'^\|\x20.*?\x20\|$'
TYPE_PRE = r'^\[PRE\d+\]$'
TYPE_IMG = r'^!\[.*?\]\(.*?\)$'

PREF_MAP = {
    'PREF_IND': PREF_IND, 
    'PREF_OL': PREF_OL, 
    'PREF_UL': PREF_UL, 
    'PREF_H1': PREF_H1, 
    'PREF_H2': PREF_H2, 
    'PREF_H3': PREF_H3, 
    'PREF_H4': PREF_H4, 
    'PREF_H5': PREF_H5, 
    'PREF_H6': PREF_H6, 
    'PREF_BQ': PREF_BQ
}

PREF_CONT_MAP = {
    'PREF_IND': '\x20' * 4, 
    'PREF_OL': '1.  ', 
    'PREF_UL': '+   ', 
    'PREF_H1': '# ', 
    'PREF_H2': '## ', 
    'PREF_H3': '### ', 
    'PREF_H4': '#### ', 
    'PREF_H5': '##### ', 
    'PREF_H6': '###### ', 
    'PREF_BQ': '> ',
}

TYPE_MAP = {
    'TYPE_TB': TYPE_TB,
    'TYPE_PRE': TYPE_PRE,
    'TYPE_IMG': TYPE_IMG,
}


RE_PRE = r'(`{3,})[\s\S]+?\1'

def match_one_pref(line):
    for tp, rgx in PREF_MAP.items():
        # print(tp, rgx, line)
        m = re.search('^' + rgx, line, re.M)
        if not m: continue
        l = len(m.group())
        line = line[l:]
        return tp, line
    return None, line
        
def match_type(line):
    for tp, rgx in TYPE_MAP.items():
        m = re.search(rgx, line)
        if m: return tp
    return 'TYPE_NORMAL'
        

def line2block(line):
    prefs = []
    while True:
        pref, line = match_one_pref(line)
        if not pref: break
        prefs.append(pref)
    line = line.strip()
    return {
        'prefs': prefs,
        'line': line,
        'type': match_type(line)
    }

def parse_blocks(md):
    lines = md.split('\n')
    lines = [l for l in lines if l.strip()]
    blocks = [line2block(l) for l in lines]
    return blocks
    
def find_next_pref(r, st, p, t):
    for i in range(st, len(r)):
        if r[i]['prefs'] == p and r[i]['type'] == t:
            return i
    return len(r)
    
def make_align(md1, md2):
    bl1, bl2 = parse_blocks(md1), parse_blocks(md2)
    idx1, idx2 = 0, 0
    res = []
    while idx1 < len(bl1) and idx2 < len(bl2):
        l1, l2 = bl1[idx1], bl2[idx2]
        p1, p2 = l1['prefs'], l2['prefs']
        t1, t2 = l1['type'], l2['type']
        if p1 == p2 and t1 == t2:
            res.append({
                'en': l1['line'],
                'zh': l2['line'],
                'prefs': p1,
                'type': t1,
            })
            idx1 += 1
            idx2 += 1
            continue
        idx1n = find_next_pref(bl1, idx1 + 1, p2, t2)
        idx2n = find_next_pref(bl2, idx2 + 1, p1, t1)
        if idx1n - idx1 < idx2n - idx2:
            while idx1 < idx1n:
                res.append({
                    'en': bl1[idx1]['line'],
                    'zh': '',
                    'prefs': bl1[idx1]['prefs'],
                    'type': bl1[idx1]['type'],
                })
                idx1 += 1
        else:
            while idx2 < idx2n:
                res.append({
                    'en': '',
                    'zh': bl2[idx2]['line'],
                    'prefs': bl2[idx2]['prefs'],
                    'type': bl2[idx2]['type'],
                })
                idx2 += 1
            
    while idx1 < len(bl1):
        res.append({
            'en': bl1[idx1]['line'],
            'zh': '',
            'prefs': bl1[idx1]['prefs'],
            'type': bl1[idx1]['type'],
        })
        idx1 += 1
    while idx2 < len(bl2):
        res.append({
            'en': '',
            'zh': bl2[idx2]['line'],
            'prefs': bl2[idx2]['prefs'],
            'type': bl2[idx2]['type'],
        })
        idx2 += 1
    return res
    
    
def align_handler(args):
    fname1 = args.en
    fname2 = args.zh
    if not fname1.endswith('.md') or \
       not fname2.endswith('.md'):
       raise ValueError('请提供两个 MD 文件！')
    md1 = open(fname1, encoding='utf8').read()
    md2 = open(fname2, encoding='utf8').read()
    res = make_align(md1, md2)
    ofname = path.basename(fname1) + '_' + path.basename(fname2) + '.yaml'
    open(ofname, 'w', encoding='utf8').write(
        yaml.safe_dump(res, allow_unicode=True))
    
def align_dir_handler(args):
    dir1 = args.en
    dir2 = args.zh
    if not path.isdir(dir1) or \
        not path.isdir(dir2):
        raise ValueError('请提供两个目录！')
    fnames = [f for f in os.listdir(dir1) if f.endswith('.md')]
    for f in fnames:
        fen = path.join(dir1, f)
        fzh = path.join(dir2, f)
        if not path.isfile(fzh):
            continue
        args.en = fen
        args.zh = fzh
        align_handler(args)

def make_totrans_handler(args):
    if path.isdir(args.fname):
        make_dir_handle(make_totrans_file)(args)
    else:
        make_totrans_file(args)

def make_totrans_file(args):
    fname = args.fname
    if not fname.endswith('.md'):
       raise ValueError('请提供 MD 文件！')
    md = open(fname, encoding='utf8').read()
    res = parse_blocks(md)
    res = [{
        'en': r['line'], 
        'prefs': r['prefs'],
        'type': r['type'],
    } for r in res]
    ofname = re.sub(r'\.\w+$', '', fname) + '.yaml'
    open(ofname, 'w', encoding='utf8').write(
        yaml.safe_dump(res, allow_unicode=True))

def rec_prefs(text, prefs):
    return ''.join([
        PREF_CONT_MAP.get(p, '')
        for p in prefs
    ]) + text

def get_line_sep(cur_blk, nxt_blk):
    if nxt_blk is None: return '\n'
    if cur_blk['type'] == 'TYPE_TB' and \
       nxt_blk['type'] == 'TYPE_TB':
       return '\n'
    if 'PREF_BQ' in cur_blk['prefs'] and \
       'PREF_BQ' in nxt_blk['prefs']:
       return '\n' + rec_prefs('', cur_blk['prefs']) + '\n'
    return '\n\n'


def fix_inner_code(zh, en):
    def repl_func(g):
        code = g.group(1)
        if  f'`{code}`' in en:
            return f'`{code}`'
        elif f'`"{code}"`' in en:
            return f'`"{code}"`'
        elif f"`'{code}'`" in en:
            return f"`'{code}'`"
        else:
            return g.group(0)
    zh =  re.sub(r'“([\x20-\x7e]+)”', repl_func, zh)
    zh =  re.sub(r'‘([\x20-\x7e]+)’', repl_func, zh)
    return zh

def check_thead_delim(text):
    return bool(re.search(r'^\|( (---|:--|:-:|--:) \|)+$', text))

def postproc_trans(trans):
    for i, blk in enumerate(trans):
        if not (blk.get('en') and blk.get('zh')):
            continue
        blk['zh'] = fix_inner_code(blk['zh'], blk['en'])
        if blk['type'] == 'TYPE_NORMAL' and blk.get('zh') == '>':
            blk['zh'] = ''
            blk['type'] = 'TYPE_BQ'
        if blk['type'] == 'TYPE_TB':
            zh = blk.get('zh', '')
            zh = re.sub(r'(?<!\\)\|(?=\S)', '| ', zh)
            zh = re.sub(r'(?<=\S)(?<!\\)\|', ' |', zh)
            if not zh.startswith('| '):
                zh = '| ' + zh
            if not zh.endswith(' |'):
                zh = zh + ' |'
            blk['zh'] = zh
            is_thead = i == 0 or trans[i - 1]['type'] != 'TYPE_TB'
            no_thead_delim = i == len(trans) - 1 or not check_thead_delim(trans[i+1]['zh'])
            if is_thead and no_thead_delim: 
                blk['no_thead_delim'] = True
        
    for i in range(len(trans) -1, -1, -1):
        blk = trans[i]
        if blk.get('no_thead_delim'):
            ncells = len(re.findall(r'(?<!\\)\|', blk['zh']))
            th_delim = '|' + ' --- |' * (ncells - 1)
            trans.insert(i + 1, {
                'en': th_delim,
                'zh': th_delim,
                'prefs': blk['prefs'],
                'type': 'TYPE_TB',
            })
            del blk['no_thead_delim']
    return trans

def rec_trans_file(args):
    fname = args.fname
    if not fname.endswith('.yaml'):
       raise ValueError('请提供 YAML 文件！')
    trans = yaml.safe_load(open(fname, encoding='utf8').read())
    trans = [it for it in trans if it.get('zh')]
    trans = postproc_trans(trans)
    trans = [it for it in trans if it.get('zh')]
    lines = [
        rec_prefs(it['zh'], it['prefs']) +
        get_line_sep(it, trans[i + 1] if i + 1 < len(trans) else None)
        for i, it in enumerate(trans)
    ]
    md = ''.join(lines)
    ofname = re.sub(r'\.\w+$', '', fname) + '.md'
    open(ofname, 'w', encoding='utf8').write(md)

def rec_trans_handler(args):
    if path.isdir(args.fname):
        make_dir_handle(rec_trans_file)(args)
    else:
        rec_trans_file(args)

def split_totrans_en(en, limit):
    if len(en) <= limit: return [en]
    ens = re.split(r'(?<=[\.\?!:;"]\x20)', en)
    return ens

def split_totrans_file(args):
    fname = args.fname
    if not fname.endswith('.yaml'):
       raise ValueError('请提供 YAML 文件！')
    totrans = yaml.safe_load(open(fname, encoding='utf8').read())
    totrans_new = []
    for it in totrans:
        en = it.get('en')
        if not en: continue
        ens = split_totrans_en(en, args.limit)
        for en in ens:
            totrans_new.append({**it, 'en': en})
    for i, it in enumerate(totrans_new):
        it['id'] = f'totrans-split-{i}'
    open(fname, 'w', encoding='utf8') \
        .write(yaml.safe_dump(totrans_new, allow_unicode=True))

def split_totrans_handler(args):
    if path.isdir(args.fname):
        make_dir_handle(split_totrans_file)(args)
    else:
        split_totrans_file(args)