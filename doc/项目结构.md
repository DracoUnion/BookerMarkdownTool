# BookerMarkdownTool 代码结构

iBooker/ApacheCN 知识库抓取与加工工具。命令行入口两个：`BookerMarkdownTool` 与 `md-tool`。

代码全部位于 `BookerMarkdownTool/` 包内，按职责分为四类模块：

## 1. 入口与命令注册

+ `__main__.py` — 唯一入口。构建顶层 `argparse` 解析器（含 LLM 公共参数：`-m/--model`、`-k/--key`、`-H/--host`、`-tm/--temp`、`-retry`、`--emb` 等），遍历各模块调用其 `reg_subparser(subparsers)` 注册子命令，最后 `args.func(args)` 派发。
+ `__init__.py` — 包元信息（`__version__` = 2026.3.25.0，SATA 协议，作者 wizardforcel）。
+ 每个子命令模块暴露 `reg_subparser(subparsers)`，在其中通过 `subparsers.add_parser("<命令名>")` 注册参数并指定 `func=xxx_hdl` 入口函数。

## 2. 共享基础设施

+ `util.py` — 通用工具函数，跨命令复用：
  + 文本解析：`ext_code_block` / `ext_cont_block`（提取代码/内容块）、`repl_code_block` / `rec_code_block`、`split_md_lines`、`group_chunks`。
  + 提示词渲染：`render_prompt(prompt, **kw)`。
  + 模型序列化：`json_dump_model`、`json_load_model`、`write_yaml_model` / `read_yaml_model`（Pydantic ↔ JSON/YAML 文件缓存）。
  + 文本相似度：`ngram_jaccard`、`ngram_coverage`（derep 去重检测）。
  + 文件与路径：`read_text` / `write_text`、`safe_mkdir`、`extname`、`md5` / `gen_objs_md5`。
+ `openai.py` — LLM 客户端层：
  + `OpenAIClient` 类，封装调用 `call_llm` / `call_llm_retry` / `call_llm_with_toolcall_retry`（最后一个是开放工具调用循环，供 `<sub_cmd>_tools.py` 类命令使用）。
  + `ToolsMixin` 类：工具型命令共享的混入（`_TOOL_PARAMS` 描述各 `tool_*` 方法的参数 Schema）。
  + Schema 构造助手：`func_schema`、`params_schema`、`model_schema`、`base_schema`、`str_list_schema`、`str_str_map_schema` 等，用于把 Pydantic 模型转成 function-calling 参数描述。
  + `dispatch_tools`：按模型返回的 tool call 分发到工具方法。

## 3. 两类子命令模块

子命令分两种组织模式：

**(a) 编排器 + 智能体模式**（复杂多步 LLM 工作流）。每个命令一组 3~4 个文件，命名固定：

+ `<sub_cmd>.py` — 编排器类 `{SubCmd}Orchestrator`，工作流每步实现为 `step_xxx(...)` 方法，`run()` 为主流程；模块内定义 `xxx_hdl(args)` 入口实例化编排器并调 `run()`，以及 `reg_subparser`。
+ `<sub_cmd>_agent.py` — 智能体类 `{SubCmd}Agent`，接收 `args`；每个大模型调用是其中一个方法，复用 `util.render_prompt`、`json_dump_model`，经 `openai.call_llm_retry` / `ask_llm_retry` 调用 LLM，并传 `parse_output` 回调（内部用 `ext_cont_block` / `ext_code_block` + `parse_obj_as` 解析）。
+ `<sub_cmd>_pmt.py` — 提示词模板，定义为全局多行字符串常量 `{XXX}_PMT`（带 `{...}` 占位符，中文，JSON 输出用三反引号包裹，否则用 `[content]...[/content]`）。
+ `<sub_cmd>_models.py` — Pydantic 模型，字段带 `Field(..., description=...)`。

现有实例：

| 命令 | 编排器 | 智能体 | 提示词 | 模型 |
| --- | --- | --- | --- | --- |
| `clean-heading` | clean_heading.py | (内联) | clean_heading_pmt.py | clean_heading_models.py |
| `md2kg` | md2kg.py | md2kg_tools.py（工具循环） | md2kg_pmt.py | md2kg_models.py |
| `md2skill` | md2skill.py | md2skill_agent.py + md2skill_chunker.py + md2skill_gen.py | md2skill_pmt.py | md2skill_models.py |
| `md2wiki` | md2wiki.py | md2wiki_agent.py | md2wiki_pmt.py | md2wiki_models.py |
| `resplit` | resplit.py | resplit_agent.py | resplit_pmt.py | resplit_models.py |
| `derep` | derep.py | derep_agent.py | derep_pmt.py | derep_models.py |

**(b) 开放工具调用循环模式**（`<sub_cmd>_tools.py` 而非 `_agent.py`）。编排器 `run()` 直接调 `call_llm_with_toolcall_retry()`；工具类继承 `ToolsMixin`，带 `_TOOL_PARAMS` 类属性描述所有 `tool_*` 方法参数 Schema，每个工作流步骤实现为一个带文件缓存（`read_yaml_model` 判非空、`write_yaml_model` 保存）的 `tool_*` 方法。示例：`md2kg.py` + `md2kg_tools.py`。

**(c) 纯文本/格式化工具模式**（不依赖 LLM，单文件即可）。直接实现 `xxx_hdl` + `reg_subparser`，多用多线程池并行：

+ 抓取下载：`dl_img.py`、`cp_img.py`、`tomd.py`。
+ 目录摘要：`summary.py`。
+ 格式整理：`fmt.py`、`opti.py`、`flatten.py`、`split.py`、`merge.py`、`ren.py`、`account.py`、`sense.py`、`clean_heading.py`（格式部分）、`fmt_chunk.py`、`trans_chunk.py`。
+ 翻译对齐：`align.py`。
+ 打包/其它：`build.py`、`comment.py`（code-comment 调 chatglm）、`misc.py`（聚合 `config-proj`、`cdrive-log` 等杂项命令）、`wx_html.py`（md → 公众号 HTML）。

## 4. 顶层包结构（`BookerMarkdownTool/BookerMarkdownTool/`）

+ 入口：`__init__.py`、`__main__.py`
+ 基础设施：`util.py`、`openai.py`
+ LLM 工作流命令：`clean_heading*`、`erchuang*`、`md2kg*`、`md2skill*`、`md2wiki*`、`resplit*`、`trans_chunk*`、`derep*`、`fmt_chunk*`
+ 格式化/抓取/打包命令：`account`、`align`、`build`、`chunker`、`comment`、`cp_img`、`dl_img`、`ext_pre`、`flatten`、`fmt`、`merge`、`misc`、`opti`、`ren`、`resplit`、`sense`、`split`、`summary`、`tomd`、`wx_html`、`erchuang`
+ 资源目录（由 `util.asset(name)` 读取）与测试（`.pytest_cache` 表明有 pytest 测试）

## 5. 关键约定（来自 AGENTS.md）

新增子命令时遵循固定范式，命名转换 `sub-cmd` → `sub_cmd`：

+ 提示词 → `<sub_cmd>_pmt.py`；模型 → `<sub_cmd>_models.py`；智能体 → `<sub_cmd>_agent.py`；编排器 → `<sub_cmd>.py`。
+ 若为工具型命令（开放循环），则不建 `_agent.py`，改建 `<sub_cmd>_tools.py`，编排器 `run()` 调 `call_llm_with_toolcall_retry()`。
+ 在 `<sub_cmd>.py` 写 `reg_subparser(subparsers)`，再到 `__main__.py` 中调用它注册。

## 6. 外部依赖

+ Python：`requests`、`pyquery`、`readability-lxml`、`pyyaml`、`openai`、`pydantic`、`json_repair`、`pyturndown`、`markdown`、`pygments`、`premailer`、`ctx_compact`（见 `openai.py`、`requirements.txt`）。
+ 可选外部工具：Pandoc（`build` 打包 EPUB）、chatglm.cpp（`code-comment`）。
+ 环境变量：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_CHAT_MODEL`、`OPENAI_VIS_MODEL`、`EMB_MODEL_PATH` 等，均可被命令行参数覆盖。
