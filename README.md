# BookerMarkdownTool

iBooker/ApacheCN 知识库抓取工具

## 安装

通过pip（推荐）：

```
pip install BookerMarkdownTool
```

从源码安装：

```
pip install git+https://github.com/DracoUnion/BookerMarkdownTool
```

需要 Node 和`to-markdown`包。

## 使用说明

```
usage: BookerMarkdownTool [-h] [-v]
                          {download,download-batch,wiki-summary,summary,docs-summary,ren-md,account,tomd,fmt,opti-md,config-proj,cdrive-log,ext-pre,rec-pre,split,merge,code-comment,align,align-dir,mk-totrans,flatten,rec-trans,split-totrans,fix-title,filter-sense,dl-img,build,cp-img}
                          ...

iBooker WIKI tool

positional arguments:
  {download,download-batch,wiki-summary,summary,docs-summary,ren-md,account,tomd,fmt,opti-md,config-proj,cdrive-log,ext-pre,rec-pre,split,merge,code-comment,align,align-dir,mk-totrans,flatten,rec-trans,split-totrans,fix-title,filter-sense,dl-img,build,cp-img}
    download            download a page
    download-batch      download pages
    wiki-summary        generate wiki summary
    summary             generate summary
    docs-summary        generate docs summary
    ren-md              rename md fname
    account             account words
    tomd                html to markdown
    fmt                 format markdown and html
    opti-md             optimize markdown
    config-proj         config proj
    cdrive-log          convert cdrive log to md
    ext-pre             extract pre from md
    rec-pre             recover pre in md
    split               split md or html
    merge               merge mds
    code-comment        add comment to code
    align               align en and zh md
    align-dir           align en and zh md
    mk-totrans          en md to yml
    flatten             flatten dir
    rec-trans           zh yaml to md
    split-totrans       split too long en
    fix-title           fix md title
    filter-sense        filter sensitive words
    dl-img              download imgs
    build               build epub
    cp-img              copy imgs in mds

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
```

## 协议

本项目基于 SATA 协议发布。

您有义务为此开源项目点赞，并考虑额外给予作者适当的奖励。

## 赞助我们

![](https://home.apachecn.org/img/about/donate.jpg)

## 另见

+   [ApacheCN 学习资源](https://docs.apachecn.org/)
+   [计算机电子书](http://it-ebooks.flygon.net)
+   [布客新知](http://flygon.net/ixinzhi/)
