# md2html.py — Markdown → HTML 转换工具

## 概述

`md2html.py` 将 Markdown 文件(默认 `README.md`)转换为带**侧边栏目录导航**的独立 HTML 文件。

- 单文件工具,拷贝即用,无需安装
- 生成的 HTML 可离线使用——CSS 和 JavaScript 全部内嵌
- 跨平台:Windows / Linux / macOS 均可运行,附 `md2html.bat` / `md2html.sh` 启动脚本

## 快速开始

### 安装依赖

```bash
pip install markdown pygments
```

(Pygments 用于代码高亮;缺 Pygments 时代码块不高亮,但转换仍可正常工作,建议安装。)

> **注意:** `md2html.bat` 优先使用 `py -3` 启动器。若 `py -3` 与 `python` 指向不同的解释器,请确认 `py -3` 对应的 Python 也已安装依赖,否则会报 `ModuleNotFoundError: No module named 'markdown'`。

### Windows

```bat
:: 双击或命令行运行(自动查找 Python)
md2html.bat

:: 等价于
python md2html.py

:: 转换任意文件
md2html.bat 文档.md -o 输出\文档.html
```

> 若提示「'md2html.bat' 不是内部或外部命令」,请改用 `.\md2html.bat` 调用(系统开启了 `NoDefaultCurrentDirectoryInExePath` 策略时,cmd 不在当前目录查找程序)。

> **双击运行:** 直接双击 `md2html.bat` 会转换其所在目录的 `README.md`,结束后窗口停留显示结果(按任意键关闭);目录中没有 `README.md` 时,窗口显示错误与用法提示后等待按键。命令行/脚本方式调用(如 `md2html.bat 文档.md`)不会停留,可直接用于管道或自动化。

### Linux / macOS

```bash
chmod +x md2html.sh
./md2html.sh                            # 转换当前目录 README.md
./md2html.sh 文档.md -o /tmp/out.html   # 转换任意文件
```

或直接用 Python:

```bash
python3 md2html.py 文档.md
```

## 命令行用法

```
usage: md2html [-h] [-o OUTPUT] [--title TITLE] [input]

positional arguments:
  input                输入的 .md 文件或包含 README.md 的目录
                       (默认:当前目录的 README.md)

options:
  -o, --output OUTPUT  输出 HTML 文件路径
                       (默认:与输入同名 .html;目录模式为 README.html)
  --title TITLE        手动指定 HTML 标题
                       (默认:文档第一个 h1,无 h1 时为输入文件名)
```

### 模式示例

| 命令 | 输入 | 输出 |
|------|------|------|
| `md2html.py` | `./README.md` | `./README.html` |
| `md2html.py docs/` | `docs/README.md` | `docs/README.html` |
| `md2html.py guide.md` | `guide.md` | `guide.html` |
| `md2html.py guide.md -o out/guide.html` | `guide.md` | `out/guide.html`(自动建目录) |
| `md2html.py --title "使用指南" guide.md` | `guide.md` | `guide.html`,标题为「使用指南」 |

### 标题与页脚

- HTML 标题来源:`--title` 参数 > 文档第一个 `#` 标题 > 输入文件名(不含扩展名)
- 侧边栏副标题:输入文件名
- 页脚:源文件名 + 生成日期(自动取当天,格式 `YYYY-MM`)

## 启动脚本

| 脚本 | 平台 | 解释器探测顺序 |
|------|------|----------------|
| `md2html.bat` | Windows | `py -3` → `python` → `python3` |
| `md2html.sh` | Linux / macOS | `python3` → `python` |

- 两个脚本都通过**自身所在目录**定位 `md2html.py`,可在任意工作目录调用(不依赖调用时的当前目录)
- 所有命令行参数原样透传,退出码原样传递(输入缺失、输出为目录等错误统一返回 1,便于脚本集成)
- 双击 `md2html.bat` 时窗口会停留到按键(便于查看结果);命令行调用无停留,退出码直接返回
- 找不到 Python 时输出错误提示并以退出码 1 结束
- 实测说明:简体中文系统(GBK 代码页)的 cmd 下,中文文件名可正常使用;其他代码页建议改用 sh 或完整路径调用

## 依赖

| 依赖 | 安装 | 说明 |
|------|------|------|
| Python | 3.8+ | Windows:python.org 安装并勾选 "Add to PATH" |
| markdown | `pip install markdown` | Markdown 解析 |
| Pygments | `pip install pygments` | 代码高亮(推荐安装) |

## 生成的 HTML 特性

### 布局与导航

```
┌──────────────────┬──────────────────────────────────────────┐
│   侧边栏导航      │          主内容区                          │
│   (300px fixed)  │          (max 1240px)                    │
│                  │                                          │
│  ┌────────────┐  │  h1 标题                                 │
│  │ 快速开始    │  │  ───────────────                         │
│  │ 目录结构    │  │  正文内容...                              │
│  │ ▸核心架构   │  │                                          │
│  │  YAML定义   │  │  ```code blocks```                      │
│  │  对象       │  │                                          │
│  │  属性       │  │  | tables | with | data |               │
│  │  ▸容器系统  │  │                                          │
│  │  ...       │  │  ## h2 章节                               │
│  └────────────┘  │  ### h3 小节                             │
│                  │                                          │
└──────────────────┴──────────────────────────────────────────┘
```

**侧边栏行为:**
- **固定定位**:滚动主内容时始终可见
- **自动高亮**:随页面滚动,当前阅读位置对应的导航项自动高亮(蓝色左边框)
- **自动滚动**:高亮项超出可视区时自动滚入视野
- **平滑跳转**:点击导航项 → 平滑滚动到对应章节
- **层级缩进**:h2(粗体)/ h3(缩进)/ h4(更深缩进)三级结构
- **移动端适配**:≤900px 宽度时侧边栏自动折叠,左上角出现汉堡菜单按钮

### 代码块

- 使用 **Pygments** 进行语法高亮
- 自动检测语言(bash / yaml / c / python / jinja2 等)
- 支持明暗双主题(跟随系统 `prefers-color-scheme`)
- 横向溢出时出现滚动条,不会撑破布局

### 表格

- 全宽显示,带交替行条纹
- 表头固定大写风格
- 圆角边框,打印时避免跨页断裂

### 明暗主题

CSS 使用 `prefers-color-scheme: dark` 媒体查询自动切换:

| 元素 | Light | Dark |
|------|-------|------|
| 背景 | `#ffffff` | `#0d1117` |
| 正文 | `#1f2328` | `#c9d1d9` |
| 代码背景 | `#f6f8fa` | `#161b22` |
| 内联代码 | `#bf1a2f` | `#ff7b72` |
| 侧边栏 | `#111318`(始终深色) | 同左 |

### 打印样式

`@media print` 下自动:
- 隐藏侧边栏和导航按钮
- 主内容全宽,黑色文字白色背景
- 表格和代码块避免跨页断裂
- 标题避免孤行

### 键盘与无障碍

| 操作 | 效果 |
|------|------|
| `Ctrl+\` | 切换移动端侧边栏(桌面端侧边栏常驻显示,无可见效果) |
| `Tab` → `Enter` | 跳过导航链接直接访问主内容 |
| 移动端点击遮罩 | 关闭侧边栏 |
| 点击导航链接后 | 移动端自动关闭侧边栏 |

## 技术实现

### 处理流程

```
输入 .md 文件(默认 README.md)
    │
    ▼ 标题提取:--title > 第一个 h1 > 文件名
    ▼ Python markdown 库 + extensions
    │  ├─ fenced_code  → 围栏代码块
    │  ├─ tables       → GFM 表格
    │  ├─ codehilite   → Pygments 语法高亮
    │  ├─ nl2br        → 单换行转 <br>
    │  └─ sane_lists   → 合理列表嵌套
    │
    ▼ 后处理
    │  ├─ 移除静态 TOC(替换为侧边栏导航)
    │  └─ 注入 h2/h3/h4 的 id 与章节编号
    │
    ▼ 注入 HTML 模板
    │  ├─ CSS (~450 行内嵌)
    │  ├─ JS  (侧边栏交互逻辑)
    │  ├─ TOC (从 markdown heading 提取的层级导航)
    │  └─ 动态内容:标题 / 源文件名 / 生成日期(YYYY-MM)
    │
    ▼
输出 .html (独立离线可用)
```

### TOC 生成策略

不从 Markdown 的 `[TOC]` 扩展生成,而是**直接从 `#` heading 行正则提取**:

```python
# 正则匹配 h2/h3/h4 heading
m = re.match(r'^(#{2,4})\s+(.+)$', line)

# 构建嵌套树结构:按 heading 层级确定父子关系
# h2 → depth=0 (根节点)
# h3 → depth=1 (挂在最近的 h2 下)
# h4 → depth=2 (挂在最近的 h3 下)
```

这样生成的 TOC 结构与 markdown toc 扩展一致(仅取 h2–h4),且更可控(可排除特定章节、调整深度等)。

### 跨平台兼容

- 路径处理统一使用 `pathlib` 并做 `.resolve()` 规范化,Windows `\` 与 Linux `/` 自动适配
- 读写均显式 `encoding='utf-8'`(输出无 BOM、`\n` 换行,浏览器兼容性最好)
- 启动时对 stdout/stderr 做 UTF-8 reconfigure,避免 Windows GBK 控制台打印中文乱码
- 启动脚本自动探测解释器:`md2html.bat` 依次尝试 `py -3` / `python` / `python3`;`md2html.sh` 依次尝试 `python3` / `python`

## 自定义

如需修改样式或行为,编辑 `md2html.py`:

| 修改目标 | 位置 |
|---------|------|
| HTML 标题来源 | `--title` 参数 / `extract_first_h1()` 函数 |
| 页脚日期格式 | `convert()` 中的 `footer_date`(`%Y-%m`) |
| 侧边栏宽度 | CSS 变量 `--sidebar-width` |
| 主内容最大宽度 | `.main` 的 `max-width` |
| 明暗主题色 | `@media (prefers-color-scheme: dark)` 块 |
| 代码高亮颜色 | `.highlight` 选择器块 |
| 移动端断点 | `@media (max-width: 900px)` |
| 打印样式 | `@media print` 块 |

## 与其他工具对比

| 工具 | 输出 | 导航 | 代码高亮 | 离线 |
|------|------|------|---------|------|
| md2html.py | 单 HTML 文件 | 侧边栏 TOC + 滚动追踪 | Pygments | ✅ |
| grip | GitHub 预览 | 无 | GitHub 风格 | ❌ (需网络) |
| markdown-pdf | PDF | 无 | 有 | ✅ |
| docsify | SPA 站点 | 侧边栏 | Prism.js | ✅ (需本地服务) |
| mdbook | 静态站点 | 侧边栏 + 搜索 | 有 | ✅ |
