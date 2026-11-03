from .util import *
import re
import hashlib
from imgyaso import pngquant

def tr_download_img(url, img_fname, args):
    try:
        print(f'{url} => {img_fname}')
        hdrs = {
            'Cookie': args.cookie,
            'Referer': args.referer,
        }
        data = request_retry(
            'GET', url, 
            headers=hdrs,
            retry=args.retry,
            check_status=not args.no_check_status,
        ).content
        data = pngquant(data)
        open(img_fname, 'wb').write(data)
    except:
        traceback.print_exc()

def dl_img_handle(args):
    fnames = [args.fname] if path.isfile(args.fname) \
        else [path.join(args.fname, f) for f in os.listdir(args.fname)]
    fnames = [f for f in fnames if f.endswith('.md')]
    if not fnames:
        raise ValueError('请提供 Makrdown 文件或目录')
    
    pool = ThreadPoolExecutor(args.file_threads)
    hdls = []
    for f in fnames:
        args = copy.deepcopy(args)
        args.fname = f
        h = pool.submit(dl_img_file, args)
        hdls.append(h)
    for h in hdls:
        h.result()

def dl_img_file(args):
    fname = args.fname
    if not fname.endswith('.md'):
        raise ValueError('请提供 Makrdown')
    print(fname)
    img_dir = path.join(path.dirname(fname), 'img')
    os.makedirs(img_dir, exist_ok=True)
    md = open(fname, encoding='utf8').read()
    mts = list(re.finditer(r'!\[[^\]]*\]\(([^\)]+)\)', md))
    pool = ThreadPoolExecutor(args.img_threads)
    hdls = []
    for m in mts:
        try:
            url = m.group(1)
            if not url.startswith('http'): continue
            hash_ = hashlib.md5(url.encode('utf8')).hexdigest()
            img_fname = path.join(
                path.dirname(fname), 'img',  f'{hash_}.png')
            h = pool.submit(tr_download_img, url, img_fname, args)
            hdls.append(h)
            md = md.replace(url, f'img/{hash_}.png')
        except KeyboardInterrupt:
            raise
        except:
            traceback.print_exc()
    
    for h in hdls:
        h.result()

    open(fname, 'w', encoding='utf8').write(md)


def reg_subparser(subparsers):
    dlimg_parser = subparsers.add_parser("dl-img", help="download imgs")
    dlimg_parser.add_argument("fname", help="md or txt file name")
    dlimg_parser.add_argument("-ft", "--file-threads", type=int, default=1, help="file threads")
    dlimg_parser.add_argument("-it", "--img-threads", type=int, default=24, help="img threads")
    dlimg_parser.add_argument("-c", "--cookie", default='', help="cookie")
    dlimg_parser.add_argument("-rf", "--referer", default='', help="referer")
    dlimg_parser.add_argument("-CS", "--no-check-status", action='store_true', help="no-check-status")
    dlimg_parser.add_argument("-r", "--retry", type=int, default=10, help="retry")
    dlimg_parser.set_defaults(func=dl_img_handle)
