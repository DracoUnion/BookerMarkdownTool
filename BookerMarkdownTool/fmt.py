import re
import os
import copy
from multiprocessing import Pool
from os import path
from pyquery import PyQuery as pq
from .util import *

num_uprscp_map = {
    '1': '¹',
    '2': '²',
    '3': '³',
    '4': '⁴',
    '5': '⁵',
    '6': '⁶',
    '7': '⁷',
    '8': '⁸',
    '9': '⁹',
    '0': '⁰',
}

def num2uprscp(text):
    return ''.join([
        num_uprscp_map.get(ch, ch)
        for ch in text
    ])

def fmt_uprscp(text):
    text =  re.sub(
        r'\^\((\d+)\)', 
        lambda g: num2uprscp(g.group(1)), 
        text
    )
    text = re.sub(
        r'\^(\d+)',
        lambda g: num2uprscp(g.group(1)), 
        text
    )
    return text

def fmt_en_zh_gap(text):
    text = re.sub(r'([\u4e00-\u9fff])([a-zA-Z0-9_])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z0-9_])([\u4e00-\u9fff])', r'\1 \2', text)
    return text

def fmt_link(text):
    RE_LINK = r'''
        \[
            https?://
            ([^\]]+)
        \]
        \(([^\)]+)\)
    '''
    text = re.sub(RE_LINK, r'[`\1`](\2)', text, flags=re.VERBOSE)
    RE_INNER_LINK = r'''
        (?<!!)
        \[([^\]]+)\]
        \(
            (?!https?://)
            [^\)]+
        \)
    '''
    text = re.sub(RE_INNER_LINK, r'\1', text, flags=re.VERBOSE)
    return text

def fmt_img(text):
    RE_INNER_IMG = r'''
        !\[([^\]]*)\]
        \(
            (?!https?://)
            ([^\)]+)
        \)
    '''

    def repl_img_func(g):
        desc, src = g.group(1), g.group(2)
        desc = desc.replace('\r', '').replace('\n', '')
        src = "img/" + path.basename(src)
        return f'![{desc}]({src})'

    return re.sub(RE_INNER_IMG, repl_img_func, text, flags=re.VERBOSE)

def fmt_chnum(text):
    text =  re.sub(
        r'第\x20*(\d{1,4})\x20*章',
        lambda g: '第' + num4d_to_zh(int(g.group(1))) + '章',
        text, 
    )
    text =  re.sub(r'(# 第.+?章)(?=。|\.\x20*)', r'\1', text)
    text =  re.sub(
        r'第\x20*(\d{1,4})\x20*(?:部分|节)',
        lambda g: '第' + num4d_to_zh(int(g.group(1))) + '部分',
        text, 
    )
    return text

def fmt_title_num(text):
    title, pos = get_md_title(text)
    if not title: return text
    m = re.search(r'\A(\d+)\x20(.+)\Z', title)
    if not m: return text
    num = int(m.group(1))
    title = num4d_to_zh(num) + '、' + m.group(2).strip()
    return text[:pos[0]] + title + text[pos[1]:]

def fmt_zh(text):
    text = fmt_en_zh_gap(text)
    text = fmt_uprscp(text)
    text = fmt_link(text)
    text = fmt_img(text)
    text = fmt_chnum(text)
    # text = fmt_title_num(text)
    text = fmt_en_zh_gap(text)
    return text

def fix_code_ind(text):
    text, pres = extreact_pre(text)
    idcs = re.findall(r'^\[PRE(\d+)\]', text, flags=re.M)
    for i in idcs:
        i = int(i)
        code = pres[i]
        m = re.search(r'^(\x20+)```', code, flags=re.M)
        if m:
            nspaces = len(m.group(1))
            code = re.sub(r'^\x20{' + str(nspaces) + '}', '', code, flags=re.M)
            pres[i] = code
    return recover_pre(text, pres)

def fix_title(fnames):
    chnum = 1
    zhch = '零一二三四五六七八九十百千'
    for f in fnames:
        print(f)
        name = path.basename(f)[:-3]
        if name == 'README' or name == 'SUMMARY': continue
        text = open(f, encoding='utf8').read()
        title, (st, _) = get_md_title(text)
        if not title:
            text = '# 第' + num4d_to_zh(chnum) + '章\n\n' + text
            chnum += 1
            open(f, 'w', encoding='utf8').write(text)
            continue
        if  title.startswith('前言') or \
            title.startswith('序言') or \
            re.search('^第[' + zhch + ']+部分', title) or \
            title.startswith('附录'):
            continue
        if  re.search('^第[' + zhch + ']+章', title) or \
            re.search('^[' + zhch + ']+、', title):
            chnum += 1
            continue
        text = text[:st] + '第' + num4d_to_zh(chnum) + '章：' + text[st:]
        chnum += 1
        open(f, 'w', encoding='utf8').write(text)

def fix_title_handler(args):
    dir = args.dir
    fnames = [f for f in os.listdir(dir) if f.endswith('.md')]
    if not args.re:
        fnames.sort()
        fix_title([path.join(dir, f) for f in fnames])
        return
    groups = {}
    for f in fnames:
        m = re.search(args.re, f)
        if not m: continue
        pref = m.group()
        groups.setdefault(pref, [])
        groups[pref].append(f)
    for fnames in groups.values():
        fnames.sort()
        fix_title([path.join(dir, f) for f in fnames])
    
def fmt_sphinx(html):
    html = rm_xml_header(html)
    rt = pq(html)
    el_dts = rt('dt.sig')
    for el in el_dts:
        el = pq(el)
        el.children('a.reference, a.anchorjs-link').remove()
        code = el.text().strip().replace('\n', ' ')
        el_pre = pq('<pre></pre>')
        el_pre.text(code)
        el2 = pq('<dt></dt>')
        el2.append(el_pre)
        el.replace_with(el2)
    el_props = rt('dl:has(dt.sig)>dd li>p:first-child>strong')
    for el in el_props:
        el = pq(el)
        el_code = pq('<code></code>')
        el_code.text(el.text())
        el.replace_with(el_code)    
    return str(rt)

def fmt_oreilly(html):
    html = html.replace('&#13;', '')
    html = re.sub(r'<code[^>]*>(\s*)</code>', r'\1', html)
    return html

def fmt_packt(html):
    RE_UNUSED_TAG = r'</?(article|section|span|header|link)[^>]*>'
    RE_DIV_START = r'<div[^>]*>\s*'
    RE_DIV_CONT = r'<div>([^<][\s\S]+?)</div>'
    RE_REPL_P = r'<p>\1</p>'
    RE_P_SNIPPLET = r'<p [^>]*class=".*?\bsnippet\b.*?"[^>]*>(.+?)</p>'
    RE_P_SRC_CODE = r'<p [^>]*class=".*?\bsource-code\b.*?"[^>]*>(.+?)</p>'
    RE_REPL_PRE = r'<pre>\1</pre>'
    RE_REPL_CODE = r'<code>\1</code>'
    RE_STRONG_INLINE = r'<strong [^>]*class=".*?\binline-code\b.*?"[^>]*>(.+?)</strong>'
    RE_STRONG_CODE = r'<strong [^>]*class=".*?\binline\b.*?"[^>]*>(.+?)</strong>'
    RE_PRE_NL = r'</pre>\s*<pre>'
    RE_SRC = r'src="(.+?)"'
    # 去除无用标签
    html = re.sub(RE_UNUSED_TAG, '', html)
    # DIV 内容
    html = re.sub(RE_DIV_START, '<div>', html)
    html = re.sub(RE_DIV_CONT, RE_REPL_P, html)
    # 代码段
    html = re.sub(RE_P_SRC_CODE, RE_REPL_PRE, html)
    html = re.sub(RE_P_SNIPPLET, RE_REPL_PRE, html)
    html = re.sub(RE_STRONG_INLINE, RE_REPL_CODE, html)
    html = re.sub(RE_STRONG_CODE, RE_REPL_CODE, html)
    html = re.sub(RE_PRE_NL, '\n', html)
    # 图像
    def img_src_repl(m):
        src = m.group(1)
        fname = path.basename(src)
        return f'src="img/{fname}"'
    html = re.sub(RE_SRC, img_src_repl, html)
    return html
    
def process_apress_pre(el_pre, root):
    el_lines = el_pre.find('.FixedLine')
    lines = []
    for i in range(len(el_lines)):
        el_line = el_lines.eq(i)
        lines.append(el_line.text())
    el_new_pre = root('<pre></pre>')
    code = re.sub(r'<[^>]*>', '', '\n'.join(lines))
    code = re.sub(r'^\x20+', '', code, flags= re.M)
    el_new_pre.text(code)
    el_pre.replace_with(el_new_pre)

def process_apress_para(el_para, root):
    el_new_para = root('<p></p>')
    el_new_para.html(el_para.html())
    el_para.replace_with(el_new_para)

def fmt_apress(html):
    html = rm_xml_header(html)
    root = pq(html)
    
    el_pres = root('.ProgramCode')
    for i in range(len(el_pres)):
        el_pre = el_pres.eq(i)
        el_new_pre = root('<pre></pre>')
        code = re.sub(r'<[^>]*>', '', el_pre.text())
        code = re.sub(r'^\x20+', '', code, flags=re.M)
        code = code.replace('\xa0', '\x20')
        el_new_pre.text(code)
        el_pre.replace_with(el_new_pre)
    
    el_codes = root('.EmphasisFontCategoryNonProportional, .FontName2, .FontName1')
    for i in range(len(el_codes)):
        el_code = el_codes.eq(i)
        el_new_code = root('<code></code>')
        el_new_code.text(el_code.text())
        el_code.replace_with(el_new_code)
        
    el_paras = root('div.Para')
    print(len(el_paras))
    for i in range(len(el_paras)):
        process_apress_para(el_paras.eq(i), root)
        
    el_lis = root('.UnorderedList, .OrderedList, pre, .Figure, .Table')
    print(len(el_lis))
    for i in range(len(el_lis)):
        el_li = el_lis.eq(i)
        el_li_parent = el_li.parent()
        if not el_li_parent.is_('p, div.Para'):
            continue
        el_li.remove()
        el_li_parent.after(el_li)
        
    el_paras = root('.CaptionNumber, .MediaObject')
    print(len(el_paras))
    for i in range(len(el_paras)):
        process_apress_para(el_paras.eq(i), root)
    
    root('.ChapterContextInformation, .AuthorGroup, .ItemNumber').remove()
    
    html = str(root)
    html = re.sub(r'</?(div|span|article|header|section|figure|figcaption)[^>]*>', '', html)
    return html
    
# @safe()
def fmt_file(args):
    mode = args.mode
    ext = extname(args.fname.lower())
    if ext not in ['html', 'md']:
        print('请提供 HTML 或 MD 文件')
        return
    print(args.fname)
    text = open(args.fname, encoding='utf8').read()
    if mode == 'zh':
        text = fmt_zh(text)
    elif mode in ['oreilly', 'orly'] and ext == "html":
        text = fmt_oreilly(text)
    elif mode == 'packt' and ext == 'html':
        text = fmt_packt(text)
    elif mode == 'apress' and ext == 'html':
        text = fmt_apress(text)
    elif mode == 'code-ind' and ext == 'md':
        text = fix_code_ind(text)
    elif mode == 'sphinx' and ext == 'html':
        text = fmt_sphinx(text)
    open(args.fname, 'w', encoding='utf8').write(text)

def fmt_handle(args):
    if path.isdir(args.fname):
        make_dir_handle(fmt_file)(args)
    else:
        fmt_file(args)