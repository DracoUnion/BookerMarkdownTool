# 仓库结构与数据格式说明

本文档说明 `cn-math-taxonomy` 仓库的目录结构、核心数据文件格式，以及如何添加新知识点。

---

## 1. 仓库整体结构

```
cn-math-taxonomy/
├── data/
│   ├── topics.json                    # 知识点节点（JSON 数组）
│   ├── dependencies.json              # 先修边（JSON 数组）
│   ├── questions.json                 # 题库（JSON 数组）
│   ├── cn-curriculum-standards.json   # 课标条目
│   ├── id-aliases.json                # 旧 ID 别名跳转表
│   ├── mappings/                      # 教材版本对照表（可选）
│   │   ├── hujiao_math.example.json
│   │   ├── hujiao_math.json
│   │   ├── sd54_math.json
│   │   ├── sujiao_math.json
│   │   └── yilin_english.json
│   ├── _qbatches/                     # 出题批次（保留对照，不部署）
│   ├── _second_pass/                  # 第二遍复核原始答案与推导
│   ├── verification_report.json       # 题库答案核验报告
│   └── second_pass_log.json           # 第二遍复核裁决与修正记录
├── scripts/
│   ├── validate.py                    # 数据校验脚本（新增数据后务必运行）
│   ├── check_figures.py
│   ├── build_primary.py               # 小学数学构建
│   ├── en_build.py / enj_build.py / enh_build.py  # 英语构建
│   ├── his_build.py / his_edges.py    # 历史构建
│   ├── geo_build.py / geo_edges.py    # 地理构建
│   ├── bio_build.py / bio_edges.py    # 生物构建
│   ├── chem_build.py / chem_edges.py  # 化学构建
│   ├── phy_build.py / phy_edges.py    # 物理构建
│   ├── zh_build.py / zhj_build.py     # 语文构建
│   ├── sci_build.py / mor_build.py    # 科学/道德与法治构建
│   └── ...                            # 各学科题目、课标、配图脚本
├── explore/                           # 知识图谱浏览（index.html, app.js 等）
├── diagnose/                          # 诊断工具（index.html, engine.js, app.js...）
├── children/                          # 孩子档案、盲区与历史
├── assets/                            # 静态资源（CSS/JS/图标/vendor 第三方库）
├── screenshots/                       # 页面截图
├── docs/                              # 各学科详细设计文档与核对记录
├── index.html                         # 首页
├── manifest.webmanifest, sw.js        # PWA
├── README.md                          # 项目总览与详细说明
├── CHANGELOG.md                       # 变更日志
├── LICENSE
└── .nojekyll, .gitignore, .github/
```

---

## 2. 核心数据文件格式

### 2.1 `data/topics.json` —— 知识点节点

顶层是一个 JSON 数组，每个元素是一个知识点对象。

**示例（数学小学节点）：**

```json
{
  "id": "cnm_p001",
  "name": "1到5各数的认识",
  "domain": "数与代数",
  "grade": 1,
  "semester": "上",
  "chapter": "一年级上册 第1单元 5以内数的认识和加、减法",
  "type": "conceptual",
  "description": "能在数量和数字之间来回，认读并写出 1 到 5。",
  "mastery_criteria": [
    "能按顺序数出 1 到 5",
    "能说出一个数的前一个和后一个"
  ],
  "diagnostic_question": {
    "question": "3 的后面一个数是几？",
    "answer": "4"
  },
  "external": false,
  "standards": [
    { "id": "cms-2022:1.NA.01", "confidence": "exact" }
  ],
  "root_reason": "一年级认数从 1 到 5 开始，前面没有更早的小学知识点。"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 稳定 id，必须符合学科编号正则（见下文“学科 id 前缀速查”）：数学小学 `cnm_pNNN`、初中 `cnm_NNN`、高中 `cnm_hNNN`；英语 `cne_p/j/h`；语文 `cnc_p/j/h`；物理 `cnp_0`/`cnp_h`；科学 `cns_p`；道德与法治 `cnd_p/j`；历史 `cnh_j/h`；地理 `cng_j/h`；生物 `cnb_j/h`；化学 `cnk_j/h`。 |
| `name` | string | 中文名称 |
| `domain` | string | 领域，必须在所属学科允许集合内（如数学：数与代数/图形与几何/统计与概率/综合与实践） |
| `grade` | int | 年级：小学 1–6，初中 7–9，高中 10–14（必修 10/11，选必 12–14）；物理高中 10–15；英语高中 10–16 |
| `semester` | string | `"上"` / `"下"`；高中均写 `"上"`，不拆上下册；九年级物理/九年级英语可写 `"全"` |
| `chapter` | string | 人教版章节，如 `"七上 第一章 有理数 1.2.1"`、`"高一 第一章 集合与常用逻辑用语 1.1"` |
| `type` | string | `conceptual` / `procedural` / `reasoning` / `application` / `modeling` |
| `description` | string | 通俗说明，1–2 句 |
| `mastery_criteria` | string[] | 掌握标准，必须是 2–3 条非空字符串 |
| `diagnostic_question` | object | `{ "question": "...", "answer": "..." }`，两者均需非空 |
| `external` | bool | 正式知识点须为 `false` |
| `standards` | object[] | 课标映射，每项 `{ "id": "<课标id>", "confidence": "exact\|inferred" }`，课标 id 必须存在于 `data/cn-curriculum-standards.json`，最多 3 条 |
| `root_reason` | string | 仅当该知识点没有任何先修边时必填（目前只有 `cnm_p001`） |
| `mappings` | object | 可选，其他教材版本对照 `{版本键: {grade, term, unit?, chapter?, note?}}` |

**校验要点：**
- `external != ("_ext_" in id)`，即外部节点 id 必须含 `_ext_`，且 `external: true`。
- 有先修边的正式知识点不必填 `root_reason`；无先修边的正式知识点**必须**填 `root_reason`。
- 每个非外部知识点不能完全孤立（既无先修也未被依赖，除非是初中道德与法治且填了 `root_reason`）。
- 物理和科学知识点可选带 `mathLinks: [{ "id": "<cnm_...>", "reason": "..." }]`，其他学科不可带。

---

### 2.2 `data/dependencies.json` —— 先修边

顶层是一个 JSON 数组，每项表示一条先修关系。

**示例：**

```json
{
  "topicId": "cnm_p002",
  "prerequisiteId": "cnm_p001",
  "strength": "hard",
  "reason": "学习「5以内数的大小」需要先掌握「1到5各数的认识」。"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `topicId` | string | 依赖方知识点 id（学 A） |
| `prerequisiteId` | string | 被依赖方知识点 id（先修 B） |
| `strength` | string | `"hard"`：不会 B 基本无法学 A；`"soft"`：对学 A 明显有帮助但非硬门槛 |
| `reason` | string | 一句中文理由，建议完整表述（不少于 9 个汉字） |

**规则：**
- 含义：**A 依赖 B**（学 A 之前需要 B）。
- 不能自环（`topicId == prerequisiteId`），不能重复边。
- 两端知识点必须都存在于 `topics.json`，且必须同属一个学科（不能跨学科边）。
- 先修年级/册次不能比本知识点更晚（由 `validate.py` 按学科分别校验）。
- 添加边后图中不能出现环路。
- 数学图做了传递约简：`hard` 边仅在存在另一条全 `hard` 路径时才被删除，`soft` 边在存在任何其他路径时即被删除。

---

### 2.3 `data/questions.json` —— 题库

顶层是一个 JSON 数组，每项是一道题。

**示例（numeric 题）：**

```json
{
  "difficulty": "basic",
  "type": "numeric",
  "prompt": "3 的后面一个数是几？",
  "answer": "4",
  "explanation": "从 1 往后数，3 的后面是 4。",
  "verify": "3+1",
  "id": "cnm_p001_q1",
  "topicId": "cnm_p001"
}
```

**示例（choice 题）：**

```json
{
  "difficulty": "basic",
  "type": "choice",
  "prompt": "4 和 2 比，哪个数大？",
  "choices": [
    { "key": "A", "text": "4" },
    { "key": "B", "text": "2" },
    { "key": "C", "text": "一样大" }
  ],
  "answer": "A",
  "explanation": "4 排在 2 的后面，所以 4 比 2 大。",
  "verify": "'4'",
  "id": "cnm_p002_q1",
  "topicId": "cnm_p002"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 必须为 `<topicId>_q<N>` 格式，如 `cnm_p001_q1`，且前缀与 `topicId` 一致 |
| `topicId` | string | 所属知识点 id，必须存在且不是外部节点 |
| `difficulty` | string | `basic` / `standard` / `challenge` |
| `type` | string | `numeric` / `choice` / `short` / `self` |
| `prompt` | string | 题干，非空；英文/中文/科学/道德与法治/历史/地理/生物/化学题干不得以「同一/上题/该题/同上」开头，不得出现「本知识点/课标/是否要求」 |
| `answer` | string | 答案，非空；choice 题必须是选项 key（A/B/C/D）；numeric 题必须可解析为数 |
| `explanation` | string | 解析，非空 |
| `choices` | object[] | choice 题必需，3–4 个选项，key 必须依次为 A、B、C、D，每项 `{ "key": "...", "text": "..." }`，可选 `figure` |
| `verify` | string | 自动核验表达式；numeric 填算式（如 `3+1`），choice 填正确选项文本（如 `'4'`） |
| `accept` | string[] | 可选，可接受的额外答案 |
| `unordered` | bool | 仅限 numeric 题且为 `true` 时有效 |
| `percent` | bool | 仅限物理 numeric 题且为 `true`（answer 写百分数的数值部分） |
| `fixed_from_source` | string | 可选，说明来源修正 |
| `figure` | string | 可选，内联示意图引用 |

**规则：**
- 每个正式知识点至少 3 道题，难度至少含 `basic` 和 `standard`；小学数学还需至少 1 道 standard 和 1 道 challenge。
- choice 题选项文字不可重复。
- 题库中 numeric + choice 应占较大比例（校验默认要求 ≥60%）。
- 每个知识点的第 1 题（`_q1`）题干应以 `topics.json` 中的 `diagnostic_question.question` 开头。

---

## 3. 学科 id 前缀速查

| 学科 | 小学 | 初中 | 高中 |
|------|------|------|------|
| 数学 | `cnm_p` | `cnm` | `cnm_h` |
| 英语 | `cne_p` | `cne_j` | `cne_h` |
| 语文 | `cnc_p` | `cnc_j` | `cnc_h` |
| 科学 | `cns_p` | — | — |
| 道德与法治 | `cnd_p` | `cnd_j` | — |
| 历史 | — | `cnh_j` | `cnh_h` |
| 地理 | — | `cng_j` | `cng_h` |
| 生物 | — | `cnb_j` | `cnb_h` |
| 化学 | — | `cnk_j` | `cnk_h` |

`validate.py` 会用正则 `^(?:cnm_(?:p|h)?|cne_[pjh]|cnp_h?|cnc_[pjh]|cns_p|cnd_[pj]|cnh_[jh]|cng_[jh]|cnb_[jh]|cnk_[jh])\d{3,}$` 严格校验 id 格式。

---

## 4. 添加新知识点的操作步骤

1. **确定 id**：按上表前缀选择，确保 id 在 `topics.json` 中唯一，不与现有 id 冲突。
2. **在 `data/topics.json` 数组末尾追加** 新知识点对象，填齐 `id`、`name`、`domain`、`grade`、`semester`、`chapter`、`type`、`description`、`mastery_criteria`、`diagnostic_question`、`external`、`standards`；如无先修边还需填 `root_reason`。
3. **在 `data/dependencies.json` 数组末尾追加** 先修边（新知识点通常至少需要一条先修边，除非是根节点并填 `root_reason`）。
4. **（建议）在 `data/questions.json` 中为新知识点添加 3–4 道题**，`id` 格式为 `<topicId>_q1` 等，并包含 `verify`。
5. **（如关联课标）确保** 该课标 id 已存在于 `data/cn-curriculum-standards.json`，否则先在该文件中补充课标条目。
6. **运行校验脚本**：
   ```bash
   python3 scripts/validate.py
   ```
   全部通过输出 `VALIDATION PASSED` 且退出码为 0；有问题会打印具体错误。若需严格模式（空 `standards` 也报错）：
   ```bash
   STRICT_STANDARDS=1 python3 scripts/validate.py
   ```
7. **（可选）运行题库核验**：
   ```bash
   python3 scripts/verify_questions.py
   ```

---

## 5. 相关文档

- `README.md`：项目总览、各学科详细说明、部署方式
- `docs/standards-mapping.md`：课标对齐说明
- `docs/questions.md`：题库格式、核验方法、统计与局限
- `docs/edition-mappings.md`：教材版本对照表说明
- `scripts/validate.py`：数据校验逻辑的权威定义
