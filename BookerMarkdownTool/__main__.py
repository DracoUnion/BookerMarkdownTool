#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

import argparse

from . import __version__
from . import account, align, build, comment, cp_img, dl_img, ext_pre
from . import flatten, fmt, merge, misc, opti, ren, sense, split, summary
from . import tomd


def main():
    parser = argparse.ArgumentParser(prog="BookerMarkdownTool", description="iBooker WIKI tool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"BookerMarkdownTool version: {__version__}")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()

    # 子命令注册：各模块中的 reg_subparser() 负责注册自己的命令
    for _mod in (
        tomd, summary, ren, account, fmt, opti, misc, ext_pre,
        split, merge, comment, align, flatten, sense, dl_img,
        build, cp_img,
    ):
        _mod.reg_subparser(subparsers)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__": main()