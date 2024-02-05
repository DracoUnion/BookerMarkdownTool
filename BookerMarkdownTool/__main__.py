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
from .split import *
from .merge import *
from .comment import *
from .align import *
from .flatten import *
from .sense import *
    
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
    dl_parser.add_argument("-r", "--remove", default='', help="selector of elements to remove")
    dl_parser.add_argument("-i", "--img-src", default='', help="prop names of <img> holding src")
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
    tomd_parser.add_argument("-l", "--lang", help="code language")
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
    ext_pre_parser.add_argument("-t", "--threads", type=int, default=8, help="thread count")
    ext_pre_parser.set_defaults(func=extract_pre_handler)

    rec_pre_parser = subparsers.add_parser("rec-pre", help="recover pre in md")
    rec_pre_parser.add_argument("fname", help="file name")
    rec_pre_parser.add_argument("-t", "--threads", type=int, default=8, help="thread count")
    rec_pre_parser.set_defaults(func=recover_pre_handler)
    
    split_parser = subparsers.add_parser("split", help="split md or html")
    split_parser.add_argument("fname", help="file name")
    split_parser.set_defaults(func=split)
    
    merge_parser = subparsers.add_parser("merge", help="merge mds")
    merge_parser.add_argument("dir", help="dir name")
    merge_parser.add_argument("-t", "--title", default='', help="title")
    merge_parser.add_argument("-l", "--lines", type=int, default=1500, help="minimum of lines of each md")
    merge_parser.add_argument("-i", "--img-pref", help="img link prefix")
    merge_parser.set_defaults(func=merge)
    
    comment_parser = subparsers.add_parser("code-comment", help="add comment to code")
    comment_parser.add_argument("fname", help="file or dir name")
    comment_parser.add_argument("-l", "--limit", type=int, default=4000, help="text limit for signle QA")
    comment_parser.add_argument("-p", "--prompt", default=CODE_COMMENT_PROMPT, help="prompt used for code comment")
    comment_parser.add_argument("-m", "--model", default='chatglm2-ggml-6b-q4_0', help="model name or path")
    comment_parser.set_defaults(func=code_comment_handle)

    align_parser = subparsers.add_parser("align", help="align en and zh md")
    align_parser.add_argument("en", help="en md name")
    align_parser.add_argument("zh", help="zh md name")
    align_parser.set_defaults(func=align_handler)

    align_dir_parser = subparsers.add_parser("align-dir", help="align en and zh md")
    align_dir_parser.add_argument("en", help="en md dir name")
    align_dir_parser.add_argument("zh", help="zh md dir name")
    align_dir_parser.set_defaults(func=align_dir_handler)

    make_to_trans = subparsers.add_parser("mk-totrans", help="en md to yml")
    make_to_trans.add_argument("fname", help="en md file name")
    make_to_trans.add_argument("-t", "--threads", type=int, default=8, help="thread count")
    make_to_trans.set_defaults(func=make_totrans_handler)

    flatten_parser = subparsers.add_parser("flatten", help="flatten dir")
    flatten_parser.add_argument("dir", help="dir name")
    flatten_parser.add_argument("-d", "--delim", default='：', help="delimiter")
    flatten_parser.set_defaults(func=flatten_dir)

    make_to_trans = subparsers.add_parser("rec-trans", help="zh yaml to md")
    make_to_trans.add_argument("fname", help="zh yaml file name")
    make_to_trans.add_argument("-t", "--threads", type=int, default=8, help="thread count")
    make_to_trans.set_defaults(func=rec_trans_handler)

    fix_title_trans = subparsers.add_parser("fix-title", help="fix md title")
    fix_title_trans.add_argument("dir", help="dir of md files")
    fix_title_trans.add_argument("--re", help="re of pref")
    fix_title_trans.set_defaults(func=fix_title_handler)
    
    sense_parser = subparsers.add_parser("filter-sense", help="filter sensitive words")
    sense_parser.add_argument("fname", help="md or txt file name")
    sense_parser.set_defaults(func=filter_sense_file)
   
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__": main()