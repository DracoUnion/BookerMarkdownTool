#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

import argparse
import requests
from readability import Document
import tempfile
import uuid
import subprocess as subp
import re
import os
import json
import yaml
from urllib.parse import quote_plus
from os import path
from pyquery import PyQuery as pq
from datetime import datetime
from collections import OrderedDict
from EpubCrawler.img import process_img
from EpubCrawler.util import safe_mkdir
from . import __version__
from .util import *
from .account import *
from .fmt import *
from .ext_pre import *
from .misc import *
from .opti import *
from .ren import *
from .summary import *
from .tomd import *
from .align import *
from .split import *
    
def main():
    parser = argparse.ArgumentParser(prog="BookerMarkdownTool", description="iBooker WIKI tool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"BookerMarkdownTool version: {__version__}")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()
    
    dl_parser = subparsers.add_parser("download", help="download a page")
    dl_parser.add_argument("url", help="url")
    dl_parser.add_argument("-e", "--encoding", default='utf-8', help="encoding")
    dl_parser.add_argument("-c", "--category", default='未分类', help="category")
    dl_parser.add_argument("-t", "--title", default='title', help="selector of article title")
    dl_parser.add_argument("-b", "--body", default='', help="selector of article body")
    dl_parser.set_defaults(func=download_handle)
    
    wiki_sum_parser = subparsers.add_parser("wiki-summary", help="generate wiki summary")
    wiki_sum_parser.set_defaults(func=wiki_summary_handle)
    
    summary_parser = subparsers.add_parser("summary", help="generate summary")
    summary_parser.add_argument("dir", help="dir")
    summary_parser.set_defaults(func=summary_handle)
    
    ren_parser = subparsers.add_parser("ren-md", help="rename md fname")
    ren_parser.add_argument("fname", help="file for dir name")
    ren_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    ren_parser.add_argument("-b", "--by", type=str, choices=['title', 'src'], default='src', help="where to extract fname")
    ren_parser.set_defaults(func=ren_md_handle)
    
    acc_parser = subparsers.add_parser("account", help="account words")
    acc_parser.add_argument("file", help="file")
    acc_parser.set_defaults(func=account_handle)

    tomd_parser = subparsers.add_parser("tomd", help="html to markdown")
    tomd_parser.add_argument("fname", help="file or dir name")
    tomd_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    tomd_parser.set_defaults(func=tomd_handle)

    fmtzh_parser = subparsers.add_parser("fmt", help="format markdown and html")
    fmtzh_parser.add_argument("mode", help="fmt mode")
    fmtzh_parser.add_argument("fname", help="file name")
    fmtzh_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    fmtzh_parser.set_defaults(func=fmt_handle)

    opti_md_parser = subparsers.add_parser("opti-md", help="optimize markdown")
    opti_md_parser.add_argument("fname", help="file name")
    opti_md_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    opti_md_parser.set_defaults(func=opti_md_handle)

    config_proj_parser = subparsers.add_parser("config-proj", help="config proj")
    config_proj_parser.add_argument("dir", help="dir name")
    config_proj_parser.set_defaults(func=config_proj)

    cdrive_log_parser = subparsers.add_parser("cdrive-log", help="convert cdrive log to md")
    cdrive_log_parser.add_argument("fname", help="log fname")
    cdrive_log_parser.set_defaults(func=convert_cdrive_log)

    ext_pre_parser = subparsers.add_parser("ext-pre", help="extract pre from md")
    ext_pre_parser.add_argument("fname", help="file name")
    ext_pre_parser.set_defaults(func=extract_pre_handler)

    rec_pre_parser = subparsers.add_parser("rec-pre", help="recover pre in md")
    rec_pre_parser.add_argument("fname", help="file name")
    rec_pre_parser.set_defaults(func=recover_pre_handler)

    align_parser = subparsers.add_parser("align", help="align en and zh md file")
    align_parser.add_argument("en", help="en file name")
    align_parser.add_argument("zh", help="zh file name")
    align_parser.set_defaults(func=align_handler)
    
    align_dir_parser = subparsers.add_parser("align-dir", help="align en and zh md file in dir")
    align_dir_parser.add_argument("en", help="en dir name")
    align_dir_parser.add_argument("zh", help="zh dir name")
    align_dir_parser.set_defaults(func=align_dir_handler)
    
    make_totrans_parser = subparsers.add_parser("make-totrans", help="md to totrans yaml")
    make_totrans_parser.add_argument("fname", help="en file name")
    make_totrans_parser.set_defaults(func=make_totrans_handler)
    
    split_parser = subparsers.add_parser("split", help="split md or html")
    split_parser.add_argument("fname", help="file name")
    split_parser.set_defaults(func=split)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__": main()