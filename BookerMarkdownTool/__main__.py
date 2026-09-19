#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

import argparse
import sys

from . import __version__
from . import account, align, build, comment, cp_img, dl_img, ext_pre
from . import flatten, fmt, merge, misc, opti, ren, sense, split, summary
from . import tomd, wx_html


def main():
    # Windows GBK 控制台对 ✓/中文等字符会报 UnicodeEncodeError，统一用 utf-8 输出
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            try:
                _stream.reconfigure(encoding='utf-8')
            except Exception:
                pass
    parser = argparse.ArgumentParser(prog="BookerMarkdownTool", description="iBooker WIKI tool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"BookerMarkdownTool version: {__version__}")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()

    # 子命令注册：各模块中的 reg_subparser() 负责注册自己的命令
    for _mod in (
        tomd, summary, ren, account, fmt, opti, misc, ext_pre,
        split, merge, comment, align, flatten, sense, dl_img,
        build, cp_img, wx_html,
    ):
        _mod.reg_subparser(subparsers)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__": main()