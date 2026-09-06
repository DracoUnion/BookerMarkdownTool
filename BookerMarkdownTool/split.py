
def split(args):
    fname  = args.fname
    if not fname.endswith('.md') and \
       not fname.endswith('.html'):
        print('请提供 MD 或者 HTML 文件')
        return
    cont = open(fname, encoding='utf8').read()
    res = cont.split('<!-- split -->')
    l = len(str(len(res)))
    ext = fname.split('.')[-1]
    pref = fname[:-len(ext)-1]
    for i, pt in enumerate(res):
        ofname = f'{pref}_{str(i).zfill(l)}.{ext}'
        print(ofname)
        open(ofname, 'w', encoding='utf8').write(pt)


def reg_subparser(subparsers):
    split_parser = subparsers.add_parser("split", help="split md or html")
    split_parser.add_argument("fname", help="file name")
    split_parser.set_defaults(func=split)