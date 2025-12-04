from .util import *
from pyquery import PyQuery as pq
from os import path
from typing import *
from GenEpub import gen_epub
from urllib.parse import unquote_plus

def get_toc(md: str, base: str) -> List[str]:
    html = md2html_pandoc(md)
    el_links = pq(html).find('a')
    toc = []
    for el in el_links:
        el = pq(el)
        link = el.attr('href')
        link = path.join(base, unquote_plus(link))
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
        print(fname)
        fname = path.join(base, unquote_plus(fname))
        if not path.isfile(fname):
            print(f'{fname} 未找到')
            continue
        img = open(fname, 'rb').read()
        imgs[path.basename(fname)] = img
        nfname = '../Images/' + path.basename(fname)
        el.attr('src', nfname)

    return str(rt)

def tr_articles(fname, art, imgs):
    md = open(fname, encoding='utf8').read()
    art.update(get_article(md))
    art['content'] = process_img(
            art['content'], 
            path.dirname(fname),
            imgs,
    )


def build(args):
    if not find_cmd_path('pandoc'):
        print('请安装 Pandoc 并设置环境变量！')
        return
    args.dir = path.abspath(args.dir)
    if not path.isdir(args.dir):
        print('请提供文档目录！')
        return 
    docrt = os.listdir(args.dir)
    if 'README.md' not in docrt or \
       'SUMMARY.md' not in docrt:
       print('请提供文档目录！')
       return

    summary = open(path.join(args.dir, 'SUMMARY.md'), encoding='utf8').read()
    toc = get_toc(summary, args.dir)
    articles = []
    imgs = {}
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    for fname in toc:
        print(fname)
        art = {}
        articles.append(art)
        h = pool.submit(tr_articles, fname, art, imgs)
        hdls.append(h)
        if len(hdls) >= args.threads:
            for h in hdls: h.result()

    for h in hdls: h.result()
    
    readme = open(path.join(args.dir, 'README.md'), encoding='utf8').read()
    readme_html = md2html_pandoc(readme)
    title = pq(readme_html).find('h1, h2, h3').eq(0).text().strip()
    if not title:
        title = path.basename(args.dir)
    epub_fname = path.join(
        path.dirname(args.dir),
        fname_escape(title) + '.epub'
    )
    gen_epub(articles, imgs, None, epub_fname)
    print(epub_fname)