# md2html 无依赖化设计(纯标准库)

日期:2026-08-13
状态:已获用户批准(方案 A:单文件内嵌自研转换器 + 内置轻量高亮器)

## 目标

去除 `markdown` 与 `pygments` 两个第三方依赖,使 `md2html.py` 成为**零依赖、纯 Python 标准库、单文件独立运行**的工具。用户反馈「总是显示 No module named markdown」(双解释器/多机器环境依赖缺失),彻底根治。

## 现状

- `md2html.py` 依赖:`markdown`(extensions: fenced_code / tables / codehilite / nl2br / sane_lists)+ Pygments(codehilite 后端)
- 现有 CSS 已定义 Pygments token 类配色(`.highlight .k/.kd/.kt/.s/.s1/.s2/.se/.c/.c1/.cm/.cp/.p/.m/.mi/.mf/.o/.nf/.na/.nb/.bp/.nc/.nv/.cpf/.w/.gh`,明暗双主题)
- 后处理管线:TOC 移除正则(`<h2>目录</h2>.*?<hr>`)→ `add_heading_ids`(h2-h4 注入 id+编号)→ 模板注入
- 测试:32 个 unittest 用例;`md2html工具说明.md` 为狗粮验收文档(用到标题/表格/围栏代码/引用/列表/粗体/行内代码/链接)

## 架构(方案 A:单文件内嵌)

`md2html.py` 内新增两个纯函数模块,替换 `import markdown`:

### 组件 1:`markdown_to_html(md_text)` — 块级解析器(~300 行)

两阶段:

**阶段一 块级切分(行扫描):**
- 标题 `#{1,6} ` → `<h1>~<h6>`(**不带 id**,id 与编号由现有 `add_heading_ids` 注入;输出格式 `<h2>标题</h2>` 与 markdown 库一致,保证 TOC 移除正则可用)
- 围栏代码块 ` ```lang `(支持 ``` 与 ~~~)→ 输出结构固定为 `<div class="highlight"><pre><code class="language-lang">…</code></pre></div>`(与 codehilite 包裹结构一致,现有 `.highlight .k` 等 CSS 配色规则才能生效);无语言时 `<code>` 不带 class;无语言的块同样用 `.highlight` 包裹结构
- GFM 表格:表头行 + `|---|:---:|---:|` 分隔行 + 数据行 → `<table><thead><tr><th>…<tbody>…`;解析对齐符但仅用于结构判定(样式由 CSS 决定,不输出 align 属性——与现有 CSS 假设一致)
- 引用 `>` 连续行(含 `> >` 嵌套) → `<blockquote>`(多行合并为一个 blockquote,内部段落再切分)
- 列表 `-`/`*`/`+`/`1.` 连续项 → `<ul>`/`<ol>`,支持嵌套(子列表按缩进挂入父 `<li>`);列表项内可含围栏代码块(缩进代码)
- 分隔线 `---`/`***`/`___`(≥3 个字符)→ `<hr>`
- 段落:空行分隔 → `<p>`;段内单个换行 → `<br>`(nl2br 语义)

**阶段二 行内解析(应用于标题/段落/表格单元格/列表项/引用内文本):**
- 转义:所有裸文本 HTML 转义(`& < > "`);解析顺序保证 span 内文本不二次转义
- 行内代码 `` `x` `` → `<code>x</code>`(内容转义)
- 粗体 `**x**` → `<strong>`;斜体 `*x*` / `_x_` → `<em>`(不支持 `***x***` 嵌套组合)
- 链接 `[text](url)` → `<a href="url">`;图片 `![alt](url)` → `<img src="url" alt="alt">`(url 属性值转义)
- 行内 HTML(如 `<br>`、`<kbd>`)原样透传(与 markdown 库行为一致,现有文档依赖)

### 组件 2:`highlight_code(code, lang)` — 轻量高亮器(~100 行)

- 输入:代码文本 + 语言标签;输出:HTML(已转义 + `<span class="...">`)
- 按行正则扫描,识别顺序:注释 → 字符串(单/双/三引号)→ 关键字 → 数字 → 函数/类名 → 内置名 → 其余
- **输出 Pygments 同款 token 类**:`k`/`kd`(关键字)、`s`/`s1`/`s2`/`se`(字符串)、`c`/`c1`(注释)、`m`/`mi`/`mf`(数字)、`nf`(函数)、`nb`/`bp`(内置)、`nc`(类)、`nv`(变量)、`o`(操作符)、`p`(标点)→ **现有明暗主题 CSS 零改动复用**
- 语言关键字表:python / bash / yaml / json / sql / c / cpp / js / html / xml;未知语言或无语言标签 → 纯文本(仅转义)
- 高亮失败(异常)→ 回退纯文本,不中断转换

## 集成改动

- `convert()`:`extensions`/`extension_configs`/`md = markdown.Markdown(...)`/`md.convert(md_text)` 整段删除,替换为 `body_html = markdown_to_html(md_text)`
- 顶部 `import markdown` 删除;docstring 的 "Requires: pip install markdown pygments" 删除
- 其余管线(TOC 移除、heading 注入、TOC 树、模板、CLI、launchers)**零改动**

## 兼容性边界(明确不支持,YAGNI)

- 不支持:任务列表 `- [x]`、脚注、引用式链接 `[t][id]`、HTML 表格属性、`***x***` 嵌套强调、围栏代码块属性(`{.python .linenos}`)
- 行内 HTML 原样透传(保留)
- 若 `md2html工具说明.md` 未使用某特性则视为验收范围外

## 错误处理

| 场景 | 行为 |
|------|------|
| 高亮器正则异常 | 捕获,该代码块回退纯文本 |
| 解析器异常 | 不吞异常(转换失败按现有 convert() 异常路径,main 返回 1) |
| 未知语言标签 | 代码块纯文本 + `class="language-xxx"` 保留(与 markdown 库一致) |

## 测试(TDD)

新增 `TestConverter`(block/inline/highlight 三组)+ 现有 32 个测试全绿:

1. 块级:标题层级、段落+br、围栏代码(带/不带语言、~~~)、表格(含对齐符)、引用多行、嵌套列表、hr、空文档
2. 行内:转义(`<script>` 文本)、行内代码、粗/斜体、链接、图片、行内 HTML 透传
3. 高亮器:python/bash/yaml/sql 关键字/字符串/注释/数字 token 类名;未知语言回退;特殊字符转义(XSS)
4. 端到端:现有 TestConvert/TestMain/TestBatch/TestRecursive 在新转换器上全部通过

## 验证

1. `python -m unittest test_md2html -v` 全绿
2. 狗粮:`python md2html.py "md2html工具说明.md"` 生成 HTML,浏览器/结构检查:TOC 项数与章节数一致、表格、代码高亮 span、明暗主题、标题编号正常
3. 在**未安装 markdown/pygments 的解释器**上运行(如 `py -3` 若不装依赖)确认零依赖
4. bat/sh 双 launcher 回归
5. `python -c "import md2html"` 确认无任何第三方 import

## 影响文件

- `md2html.py`:修改(+~400 行转换器/高亮器,-依赖导入与配置)
- `test_md2html.py`:新增 TestConverter
- `md2html工具说明.md` + 生成的 HTML:依赖章节、技术实现章节更新
- 其他文件(launchers、模板 CSS/JS)零改动
