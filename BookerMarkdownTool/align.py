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
    if cur_blk['type'] == TYPE_TB and \
       nxt_blk['type'] == TYPE_TB:
       return '\n'
    if PREF_BQ in cur_blk['prefs'] and \
       PREF_BQ in nxt_blk['prefs']:
       return '\n'
    return '\n\n'

def rec_trans(args):
    fname = args.fname
    if not fname.endswith('.yaml'):
       raise ValueError('请提供 YAML 文件！')
    trans = yaml.safe_load(open(fname, encoding='utf8').read())
    trans = [it for it in trans if it.get('zh')]
    lines = [
        rec_prefs(it['zh'], it['prefs']) +
        get_line_sep(it, lines[i + 1] if i < len(lines) else None)
        for i, it in enumerate(trans)
    ]
    md = ''.join(lines)
    ofname = re.sub(r'\.\w+$', '', fname) + '.md'
    open(ofname, 'w', encoding='utf8').write(md)

