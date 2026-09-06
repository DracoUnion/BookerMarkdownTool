# BookerMarkdownTool

> iBooker/ApacheCN 知识库抓取与加工工具

一套用于抓取网页、将其整理为规范的 Markdown 知识库，并进一步生成目录、格式排版、中英对照翻译、打包 EPUB 的命令行工具。

全部命令既可以用 `BookerMarkdownTool` 调用，也可以用 `md-tool` 调用：

```
BookerMarkdownTool <子命令> [参数]
md-tool <子命令> [参数]
```

输入 `BookerMarkdownTool -v` 查看版本号，`BookerMarkdownTool -h` 或直接不带参数查看帮助。

## 目录

+   [安装](#安装)
+   [命令速查](#命令速查)
+   [命令详解](#命令详解)
+   [典型工作流](#典型工作流)
+   [注意事项](#注意事项)
+   [协议](#协议)
+   [赞助我们](#赞助我们)
+   [另见](#另见)

## 安装

通过 pip 安装（推荐）：

```
pip install BookerMarkdownTool
```

从源码安装：

```
pip install git+https://github.com/DracoUnion/BookerMarkdownTool
```

本地开发时可用可编辑模式安装：

```
pip install -e .
```

### 依赖

Python 依赖（安装时自动拉取）：`requests`、`pyquery`、`readability-lxml`、`pyyaml`、`EpubCrawler`、`imgyaso`、`pyturndown`。HTML 转 Markdown 依赖 `pyturndown`（Turndown 的 Python 移植，不需要 Node.js）。

可选的外部工具（不在 pip 依赖中，按需安装）：

+   **Pandoc**：`build` 命令打包 EPUB 时需要，请安装后加入 `PATH`。
+   **chatglm**（chatglm.cpp）：`code-comment` 命令给代码加注释时需要，请下载后将可执行文件所在目录加入 `PATH`。

## 命令速查

| 命令 | 功能 | 常见参数 |
| --- | --- | --- |
| `download` | 抓取单个网页并转存为 Markdown | `<url>` `-e` `-c` `-t` `-b` `-r` `-i` `-p` `--retry` |
| `download-batch` | 按 URL 列表文件批量抓取 | `<文件>` `-t` `-c` `-p` `--retry` |
| `tomd` | HTML 转 Markdown（文件或目录） | `<路径>` `-t` `-l` |
| `ren-md` | 按标题/原文链接重命名 md | `<路径>` `-b title\|src` `-t` |
| `dl-img` | 下载 md 中的外链图片 | `<文件>` |
| `cp-img` | 复制 md 引用的图片到目标目录 | `<文件> <src> <dst>` |
| `summary` | 为某个目录生成 `SUMMARY.md` | `<目录>` |
| `wiki-summary` | 为 `docs/` 生成带分类的 `SUMMARY.md` | （无参数） |
| `docs-summary` | 为 docs 风格项目生成 `SUMMARY.md` | `<目录>` `-a` |
| `fmt` | 格式化 Markdown / HTML | `<模式> <路径> -t` |
| `opti-md` | 优化 Markdown 并统一写法 | `<路径> -t` |
| `fix-title` | 自动补充“第 N 章”标题 | `<目录>` `--re` |
| `flatten` | 拍平嵌套目录 | `<目录>` `-d` |
| `split` | 按 `<!-- split -->` 拆分文件 | `<文件>` |
| `merge` | 合并多个 md 并按行数分册 | `<目录> -t -l -i -r` |
| `account` | 按 Word 规则统计字数 | `<文件>` |
| `filter-sense` | 过滤腾讯敏感词 | `<文件>` |
| `ext-pre` | 抽取代码块到 `.json` 占位 | `<路径> -t` |
| `rec-pre` | 恢复被抽取的代码块 | `<路径> -t` |
| `align` | 中英文 md 逐块对齐为 yaml | `<en.md> <zh.md>` |
| `align-dir` | 批量对齐两个目录 | `<en目录> <zh目录>` |
| `mk-totrans` | 英文 md 转为翻译用 yaml | `<路径> -t` |
| `split-totrans` | 拆分过长的英文句子 | `<yaml> -t -l` |
| `rec-trans` | 翻译后的 yaml 还原为 md | `<路径> -t` |
| `build` | 打包生成 EPUB | `<目录> -t` |
| `config-proj` | 交互式配置站点项目 | `<目录>` |
| `cdrive-log` | CDrive 上传日志转 md 表格 | `<文件>` |
| `code-comment` | 用 chatglm 给代码加注释 | `<路径> -l -p -m` |

> 多数命令支持目录输入并搭配 `-t/--threads`（默认 8）并行处理，如 `fmt`、`opti-md`、`ren-md`、`ext-pre`、`rec-pre`、`mk-totrans`、`rec-trans`、`split-totrans`。

## 命令详解

### 抓取与下载

#### `download`

抓取一个网页，自动提取标题与正文，下载文中图片，保存为带元信息的 Markdown：

```
BookerMarkdownTool download <url> [选项]
```

+ 输出文件：`docs/<标题>.md`，图片保存在 `docs/img/`。
+ 文件头写入 YAML 元信息块（`wiki-summary` 依赖它分类）：

```
<!--yml
category: 未分类
date: 2026-09-06 10:00:00
-->
```

+ 标题在 `docs/` 已存在时自动跳过，适合断点续抓。

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `-e, --encoding` | 网页编码 | `utf-8` |
| `-c, --category` | 文章分类（写入元信息） | `未分类` |
| `-t, --title` | 标题的 CSS 选择器 | `title` |
| `-b, --body` | 正文的 CSS 选择器（留空则用 readability 自动提取） | 空 |
| `-r, --remove` | 需要移除元素的选择器 | 空 |
| `-i, --img-src` | `<img>` 中承载图片地址的属性名，逗号分隔 | 空 |
| `-p, --proxy` | HTTP/HTTPS 代理 | 无 |
| `--retry` | 失败重试次数 | `3` |

示例：

```
BookerMarkdownTool download https://example.com/a.html
BookerMarkdownTool download https://example.com/a.html -e gb2312 -b '.article' -c '编程语言'
```

#### `download-batch`

按 URL 列表文件批量抓取，文件中每行一个 URL：

```
BookerMarkdownTool download-batch <urls.txt> [选项]
```

选项与 `download` 相同，另有 `-t/--threads`（默认 8）控制并发。

示例：

```
BookerMarkdownTool download-batch urls.txt -t 16
```

#### `tomd`

把 HTML 转成同名 `.md`，支持文件或目录：

```
BookerMarkdownTool tomd <路径> [选项]
```

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `-t, --threads` | 目录模式下的并行数 | `8` |
| `-l, --lang` | 为无语言的代码块统一指定语言（如 `python`） | 无 |

#### `ren-md`

按规则重命名 md 文件名（非法字符自动替换为 `-`）：

```
BookerMarkdownTool ren-md <文件或目录> [选项]
```

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `-b, --by` | `src`：从版权行 `原文：…` 的链接路径提取 slug；`title`：从 `# 标题` 提取 | `src` |
| `-t, --threads` | 目录模式下的并行数 | `8` |

#### `dl-img`

扫描 md 中的外链图片，下载到同目录 `img/`，以 `md5(URL).png` 命名并替换引用：

```
BookerMarkdownTool dl-img <文件>
```

#### `cp-img`

扫描 md 中用 `![…](图片名)` 引用的图片，把它们从 `src` 目录复制到 `dst` 目录（目标已存在则覆盖）：

```
BookerMarkdownTool cp-img <文件> <src目录> <dst目录>
```

### 目录与摘要

#### `summary`

为指定目录中的 md 生成 `SUMMARY.md`（`README.md` 排在最前，其余按文件名顺序）：

```
BookerMarkdownTool summary <目录>
```

#### `wiki-summary`

读取当前目录下 `docs/` 中带元信息块的 md，按 `category` 分类，生成树状的 `SUMMARY.md`：

```
BookerMarkdownTool wiki-summary
```

生成效果（分类、文章链接按书名号目录编码）：

```
+   前端
    +   [Foo](docs/foo)
```

#### `docs-summary`

为 docs 风格项目（`<目录>/docs/*/README.md`）生成 `SUMMARY.md`：

```
BookerMarkdownTool docs-summary <目录> [选项]
```

| 选项 | 说明 |
| --- | --- |
| `-a, --all` | 同时把各子目录自己的 `SUMMARY.md` 子树追加进总目录 |

### 格式化与整理

#### `fmt`

按模式格式化 Markdown 或 HTML，支持文件或目录：

```
BookerMarkdownTool fmt <模式> <路径> [选项]
```

| 模式 | 适用文件 | 作用 |
| --- | --- | --- |
| `zh` | md / html | 中文排版：中英文之间加空格、`^(n)` 转上标、链接与图片路径规范化、阿拉伯数字章号转中文数字 |
| `oreilly` / `orly` | html | 清理 O'Reilly 网站导出的 HTML |
| `packt` | html | 清理 Packt HTML（无用标签、snippet、内联代码、图片路径） |
| `apress` | html | 清理 Apress HTML（ProgramCode、Para 等结构） |
| `sphinx` | html | 清理 Sphinx HTML（`dt.sig` 签名转 `<pre>`） |
| `code-ind` | md | 修正代码块缩进（内部先用占位符保护代码块） |

#### `opti-md`

优化 md 写法（文件或目录）：图片路径 `../Images/` 归一为 `img/`、去掉残留的章节日期标记、规整代码块围栏等：

```
BookerMarkdownTool opti-md <路径> [选项]
```

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `-t, --threads` | 目录模式并行数 | `8` |

#### `fix-title`

为目录中的 md 自动补“第 N 章：”标题，编号连续，自动跳过前言、序言、部分、附录：

```
BookerMarkdownTool fix-title <目录> [选项]
```

| 选项 | 说明 |
| --- | --- |
| `--re` | 按文件名匹配到的前缀分组，各组独立编号（适合多篇合集整理） |

#### `flatten`

拍平嵌套目录：把子目录中的文件全部移到根目录，路径分隔符替换为指定分隔符（默认全角冒号 `：`）：

```
BookerMarkdownTool flatten <目录> [-d 分隔符]
```

#### `split`

按 `<!-- split -->` 分页标记把 md / html 拆成多个文件：

```
BookerMarkdownTool split <文件>
```

输出 `book_00.md`、`book_01.md` …（按总份数补齐前导零）。

#### `merge`

合并目录中的多个 md，并近似每个文件约 N 行再分册：

```
BookerMarkdownTool merge <目录> [选项]
```

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `-t, --title` | 分册标题（缺省时从 `README.md` 读取） | 空 |
| `-l, --lines` | 每册最少行数 | `1500` |
| `-i, --img-pref` | 批量把 `img/` 前替换为远程前缀（以 `/` 结尾） | 无 |
| `-r, --recur` | 递归子目录（跳过 `README.md`、`SUMMARY.md`） | 关闭 |

输出 `目录-merge-00.md` 等，册标题为“第 N 章”。

#### `account`

按 Word 规则统计 md 字数（自动剔除代码块与图片；一个汉字或中文标点算一字，一个连续英文序列算一字）：

```
BookerMarkdownTool account <文件>
```

输出中文字数、英文字数、总字数。

#### `filter-sense`

用内置的腾讯敏感词表过滤 md / txt：命中词按字插入 `丨` 进行分隔：

```
BookerMarkdownTool filter-sense <文件>
```

#### `ext-pre` / `rec-pre`

`fmt`、`opti-md` 等在代码块上做正则替换时可能误伤代码，可以先把代码块提取出来保护：

```
BookerMarkdownTool ext-pre <路径>       # 代码块 → 同名 .json，正文用 [PRE0] 占位
BookerMarkdownTool rec-pre <路径>       # 读回 .json，把占位符还原为代码块并删除 json
```

支持文件或目录（`-t/--threads` 默认 8）。

### 翻译与对齐

以下命令构成中英对照翻译流水线：`mk-totrans` 把英文 md 切成可翻译的块 → 人工/机器翻译 `en` 字段为 `zh` → `rec-trans` 还原成 md。

#### `mk-totrans`

解析英文 md，保留标题、列表、引用、表格、代码占位等结构信息，输出同名 `.yaml`：

```
BookerMarkdownTool mk-totrans <路径> [选项]
```

#### `split-totrans`

把 yaml 中过长的英文句子按句号等标点边界拆分，并附上 `id`，便于分段翻译：

```
BookerMarkdownTool split-totrans <yaml> [选项]
```

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `-l, --limit` | 句长阈值（超长才拆分） | `4000` |

#### `rec-trans`

读取已填充 `zh` 字段的 yaml，恢复缩进/标题/列表/引用前缀、内联代码、表格表头分隔线，输出同名 `.md`：

```
BookerMarkdownTool rec-trans <路径> [选项]
```

#### `align` / `align-dir`

把英文 md 与中文 md 逐块对齐，输出 `${en}`_`${zh}`.yaml（每个条目含 `en`、`zh`、结构前缀与类型）：

```
BookerMarkdownTool align <en.md> <zh.md>
BookerMarkdownTool align-dir <en目录> <zh目录>
```

### 打包与发布

#### `build`

根据目录里的 `README.md` 与 `SUMMARY.md` 生成 EPUB（需要 Pandoc）：

```
BookerMarkdownTool build <目录> [选项]
```

按 `SUMMARY.md` 的链接顺序抽取章节与图片，输出到父目录的 `<标题>.epub`。`-t/--threads` 控制并行数（默认 8）。

#### `config-proj`

交互式配置 ApacheCN 风格的文档站点项目，要求目录中包含 `README.md`、`index.html`、`CNAME`：

```
BookerMarkdownTool config-proj <目录>
```

按提示输入中文名、英文名、英文链接、域名前缀、颜色，工具会自动把三个文件中的 `{name}`、`{nameEn}`、`{urlEn}`、`{domain}`、`{color}`、`{repo}` 等占位符替换为实际值。

#### `cdrive-log`

把 CDrive 上传日志转换为 Markdown 表格，输出 `<文件名>.md`：

```
BookerMarkdownTool cdrive-log <log文件>
```

#### `code-comment`

使用 chatglm.cpp 给代码逐行加注释，输出 `<文件>.md`（需要 `chatglm` 命令在 PATH 中）：

```
BookerMarkdownTool code-comment <文件或目录> [选项]
```

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `-l, --limit` | 单次问答的文本上限 | `4000` |
| `-p, --prompt` | 提问模板 | 内置“请给以下代码的每一行添加注释” |
| `-m, --model` | 模型名或模型文件路径 | `chatglm2-ggml-6b-q4_0` |

## 典型工作流

以把一份在线图书整理为 ApacheCN 风格知识库为例：

**1. 抓取页面**

```
BookerMarkdownTool download-batch urls.txt -c '主题分类'
# 或逐个抓取
BookerMarkdownTool download https://example.com/xxx.html
```

**2. 生成目录**

```
BookerMarkdownTool wiki-summary        # docs/ 下按分类生成 SUMMARY.md
```

**3. 格式化与优化**

```
BookerMarkdownTool ext-pre docs          # 先保护代码块（如有需要）
BookerMarkdownTool fmt zh docs -t 8     # 中文排版
BookerMarkdownTool opti-md docs         # 统一图片路径等写法
BookerMarkdownTool rec-pre docs         # 恢复代码块
BookerMarkdownTool fix-title docs       # 补齐章节号
BookerMarkdownTool flatten docs         # 若需要拍平子目录
```

**4. 字数统计与敏感词检查**

```
BookerMarkdownTool account docs/xxx.md
BookerMarkdownTool filter-sense docs/xxx.md
```

**5. 打包 EPUB**

```
BookerMarkdownTool build docs -t 8
```

**批量导出 / 手工整编**：`tomd` 转单页 HTML，`split` 拆分、`merge` 合并分册。

## 注意事项

+ 抓取遵循目标站点 robots 协议与相关规定，请仅抓取有授权的内容。
+ `download` 的 `-r/--remove` 当前按选择器移除指定元素。
+ 多数命令会直接改写源文件，先备份或放到临时目录再处理。
+ `build`、`code-comment` 依赖外部工具 Pandoc、chatglm.cpp，请先安装并配置 `PATH`。

## 协议

本项目基于 SATA 协议发布。

您有义务为此开源项目点赞，并考虑额外给予作者适当的奖励。

## 赞助我们

![](https://home.apachecn.org/img/about/donate.jpg)

## 另见

+   [ApacheCN 学习资源](https://docs.apachecn.org/)
+   [计算机电子书](http://it-ebooks.flygon.net)
+   [布客新知](http://flygon.net/ixinzhi/)