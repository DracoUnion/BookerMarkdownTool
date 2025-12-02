from .util import *
from pyquery import PyQuery as pq
from os import path
from typing import *

def get_toc(md: str, base: str) -> List[str]:
    html = md2html_pandoc(md)
    el_links = pq(html).find('a')
    toc = []
    for el in el_links:
        el = pq(el)
        link = el.attr('href')
        link = path.join(base, link)
        toc.append(link)
    return toc

def get_article(md: str) -> Dict[str, str]:
    html = md2html_pandoc(md)
    rt = pq(html)
    el_title = rt.find('h1, h2, h3').eq(0)
    title = el_title.text().strip()
    el_title.remove()
    content = (
        rt.find('body').html()
        if rt.find('body')
        else str(rt)
    )
    return {'title': title, 'content': content}

def process_img(html: str, base: str, imgs: Dict[str, bytes]) -> str:
    rt = pq(html)
    el_imgs = rt.find('img')
    for el in el_imgs:
        el = pq(el)
        fname = el.attr('src')
        if re.search('^https?://', fname):
            continue
        fname = path.join(base, fname)
        if not path.isfile(fname):
            print(f'{fname} 未找到')
            continue
        img = open(fname, 'rb').read()
        imgs[path.basename(fname)] = img
        nfname = '../Images/' + path.basename(fname)
        el.attr('src', nfname)

    return str(rt)