# md2html.py 跨平台通用化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 md2html.py 适配为 Windows/Linux 通用的 Markdown→HTML 工具(多模式 CLI、动态标题/日期、启动脚本),并更新说明文档。

**Architecture:** 保持单文件结构。新增 `extract_first_h1` / `resolve_paths` / `build_parser` / `main` 四个纯函数,`convert()` 增加 `title` 参数并把模板中三处硬编码改为 f-string 变量;配套 `md2html.bat` / `md2html.sh` 启动脚本。测试用 stdlib `unittest`,零新增依赖。

**Tech Stack:** Python 3.8+(实测 3.12)、argparse、pathlib、python-markdown、stdlib unittest

**Spec:** `docs/superpowers/specs/2026-08-13-md2html-cross-platform-design.md`

**注意:** 本目录不是 git 仓库,各任务末尾的 commit 步骤省略(如需版本控制,先执行 `git init`)。

**测试运行命令(本机 Windows,Git Bash):**
- 单元测试:`python -m unittest test_md2html -v`
- 语法检查:`python -m py_compile md2html.py`
- shell 脚本语法:`bash -n md2html.sh`
- 通过 cmd 调用 bat:`cmd //c md2html.bat <参数>`

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `test_md2html.py` | 新建 | unittest 测试(新行为全覆盖) |
| `md2html.py` | 修改 | 核心转换逻辑 + 新 CLI |
| `md2html.bat` | 新建 | Windows 启动脚本(探测 py/python/python3) |
| `md2html.sh` | 新建 | Linux/macOS 启动脚本(探测 python3/python) |
| `md2html工具说明.md` | 修改 | 文档更新(双平台用法、CLI 参数表) |

## 新函数接口约定(全计划一致)

```python
extract_first_h1(md_text: str) -> str | None          # 第一个 h1 的纯文本,无则 None
build_parser() -> argparse.ArgumentParser              # CLI 定义
resolve_paths(args, cwd=None) -> (Path, Path, str|None) | None
                                                       # (输入, 输出, title);输入不存在时打印 ERROR 并返回 None
_setup_console_encoding() -> None                      # stdout/stderr UTF-8 reconfigure
main(argv=None) -> int                                 # 返回退出码;__main__ 调 sys.exit(main())
convert(input_path, output_path, title=None) -> None   # 新签名;title=None 时自动提取
```

---

### Task 1: 编写失败测试(新行为全覆盖)

**Files:**
- Create: `test_md2html.py`

- [ ] **Step 1: 写测试文件**

完整内容:

```python
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import md2html


class TestExtractFirstH1(unittest.TestCase):
    def test_found(self):
        self.assertEqual(md2html.extract_first_h1('# Hello World\n\nbody'), 'Hello World')

    def test_skips_h2(self):
        self.assertEqual(md2html.extract_first_h1('## Not h1\n# Real h1'), 'Real h1')

    def test_keeps_inline_formatting(self):
        self.assertEqual(md2html.extract_first_h1('# **Bold** Title'), '**Bold** Title')

    def test_none_when_no_h1(self):
        self.assertIsNone(md2html.extract_first_h1('no headings here'))


class TestResolvePaths(unittest.TestCase):
    def _args(self, **kw):
        defaults = dict(input=None, output=None, title=None)
        defaults.update(kw)
        return SimpleNamespace(**defaults)

    def test_no_args_readme_in_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / 'README.md').write_text('# T', encoding='utf-8')
            inp, out, title = md2html.resolve_paths(self._args(), cwd=cwd)
            self.assertEqual(inp, cwd / 'README.md')
            self.assertEqual(out, cwd / 'README.html')
            self.assertIsNone(title)

    def test_no_args_missing_readme_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(md2html.resolve_paths(self._args(), cwd=Path(tmp)))

    def test_dir_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / 'README.md').write_text('# T', encoding='utf-8')
            inp, out, _ = md2html.resolve_paths(self._args(input='.'), cwd=cwd)
            self.assertEqual(inp, cwd / 'README.md')
            self.assertEqual(out, cwd / 'README.html')

    def test_file_mode_default_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / 'guide.md').write_text('# T', encoding='utf-8')
            inp, out, _ = md2html.resolve_paths(self._args(input='guide.md'), cwd=cwd)
            self.assertEqual(inp, cwd / 'guide.md')
            self.assertEqual(out, cwd / 'guide.html')

    def test_file_mode_explicit_output_creates_dir_later(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / 'guide.md').write_text('# T', encoding='utf-8')
            inp, out, _ = md2html.resolve_paths(
                self._args(input='guide.md', output='out/result.html'), cwd=cwd)
            self.assertEqual(inp, cwd / 'guide.md')
            self.assertEqual(out, cwd / 'out' / 'result.html')

    def test_missing_input_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(md2html.resolve_paths(self._args(input='nope.md'), cwd=Path(tmp)))

    def test_title_passthrough(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / 'README.md').write_text('# T', encoding='utf-8')
            _, _, title = md2html.resolve_paths(
                self._args(input='README.md', title='Custom'), cwd=cwd)
            self.assertEqual(title, 'Custom')


class TestConvert(unittest.TestCase):
    def _convert(self, md_text, title=None, name='doc.md'):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / name
            out = Path(tmp) / 'out.html'
            src.write_text(md_text, encoding='utf-8')
            md2html.convert(src, out, title=title)
            return out.read_text(encoding='utf-8')

    def test_title_from_first_h1(self):
        html = self._convert('# My Guide\n\n## Section\nbody')
        self.assertIn('<title>My Guide</title>', html)
        self.assertIn('<h2>My Guide</h2>', html)

    def test_title_fallback_to_filename_stem(self):
        html = self._convert('no h1 here', name='fallback.md')
        self.assertIn('<title>fallback</title>', html)

    def test_title_override(self):
        html = self._convert('# Doc Title', title='Custom')
        self.assertIn('<title>Custom</title>', html)
        self.assertNotIn('<title>Doc Title</title>', html)

    def test_title_html_escaped(self):
        html = self._convert('# A <B> & C')
        self.assertIn('<title>A &lt;B&gt; &amp; C</title>', html)

    def test_source_name_and_dynamic_date_in_footer(self):
        html = self._convert('# T', name='guide.md')
        self.assertIn('Auto-generated from guide.md', html)
        self.assertIn(datetime.now().strftime('%Y-%m'), html)
        self.assertNotIn('v2.0', html)

    def test_no_hardcoded_autogen_title(self):
        html = self._convert('# T')
        self.assertNotIn('Autogen — GT SDK', html)
        self.assertNotIn('GT SDK Code Generator', html)


class TestMain(unittest.TestCase):
    def test_main_missing_input_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                self.assertEqual(md2html.main(['nope.md']), 1)
            finally:
                os.chdir(old)

    def test_main_generates_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                Path('README.md').write_text('# CLI Test', encoding='utf-8')
                self.assertEqual(md2html.main([]), 0)
                html = Path('README.html').read_text(encoding='utf-8')
                self.assertIn('<title>CLI Test</title>', html)
            finally:
                os.chdir(old)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest test_md2html -v`
Expected: FAIL/ERROR——`TestExtractFirstH1`/`TestResolvePaths` 报 `AttributeError: module 'md2html' has no attribute 'extract_first_h1'`(或 `resolve_paths`);`TestConvert` 报 `TypeError: convert() got an unexpected keyword argument 'title'`;`TestMain` 报 `AttributeError: module 'md2html' has no attribute 'main'`。通过数 0。

---

### Task 2: 实现 extract_first_h1 / CLI 函数 / 新 main

**Files:**
- Modify: `md2html.py:1-6`(顶部 import 区)
- Modify: `md2html.py:739-747`(`__main__` 块,整体替换)

- [ ] **Step 1: 更新顶部 import**

`md2html.py` 第 1-8 行原内容:

```python
#!/usr/bin/env python3
"""
Convert README.md to README.html with sidebar TOC navigation.
Requires: pip install markdown pygments
"""
import re
import markdown
from pathlib import Path
```

替换为:

```python
#!/usr/bin/env python3
"""
Convert a Markdown file into a standalone HTML page with sidebar TOC navigation.
Requires: pip install markdown pygments
"""
import argparse
import html
import re
import sys
from datetime import datetime
from pathlib import Path

import markdown
```

- [ ] **Step 2: 在 slugify 之后新增 extract_first_h1**

在 `slugify` 函数定义之后(原第 16 行 `return slug` 之后)插入:

```python
def extract_first_h1(md_text):
    """Return the text of the first h1 heading, or None if the document has none."""
    for line in md_text.split('\n'):
        m = re.match(r'^#\s+(.+)$', line)
        if m:
            return m.group(1).strip()
    return None
```

- [ ] **Step 3: 用 CLI 函数整体替换 `__main__` 块**

`md2html.py` 第 739-747 行原内容:

```python
if __name__ == '__main__':
    import sys
    workdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    readme = workdir / 'README.md'
    output = workdir / 'README.html'
    if not readme.exists():
        print(f"ERROR: {readme} not found")
        sys.exit(1)
    convert(str(readme), str(output))
```

替换为:

```python
def build_parser():
    parser = argparse.ArgumentParser(
        prog='md2html',
        description='Convert a Markdown file into a standalone HTML page '
                    'with sidebar TOC navigation.')
    parser.add_argument(
        'input', nargs='?', default=None,
        help='input .md file, or a directory containing README.md '
             '(default: README.md in the current directory)')
    parser.add_argument(
        '-o', '--output', default=None,
        help='output HTML file path '
             '(default: same name as the input with .html extension)')
    parser.add_argument(
        '--title', default=None,
        help='HTML title (default: the first h1 heading in the document, '
             'or the input filename)')
    return parser


def resolve_paths(args, cwd=None):
    """Resolve (input_path, output_path, title) from parsed args.
    Returns None (after printing an error) if the input does not exist.
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    dir_mode = False

    if args.input is None:
        dir_mode = True
        input_path = cwd / 'README.md'
    else:
        p = Path(args.input)
        input_path = p if p.is_absolute() else cwd / p
        if input_path.is_dir():
            dir_mode = True
            input_path = input_path / 'README.md'

    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        return None

    if args.output is not None:
        p = Path(args.output)
        output_path = p if p.is_absolute() else cwd / p
    elif dir_mode:
        output_path = input_path.parent / 'README.html'
    else:
        output_path = input_path.with_suffix('.html')

    return input_path, output_path, args.title


def _setup_console_encoding():
    """Windows consoles default to GBK; reconfigure stdout/stderr to UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None):
    _setup_console_encoding()
    args = build_parser().parse_args(argv)
    resolved = resolve_paths(args)
    if resolved is None:
        return 1
    input_path, output_path, title = resolved
    output_path.parent.mkdir(parents=True, exist_ok=True)
    convert(input_path, output_path, title=title)
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: 语法检查**

Run: `python -m py_compile md2html.py`
Expected: 无输出,退出码 0

- [ ] **Step 5: 运行测试**

Run: `python -m unittest test_md2html -v`
Expected:`TestExtractFirstH1`、`TestResolvePaths`、`TestMain` 全部 PASS;`TestConvert` 仍 FAIL/ERROR(`convert` 尚未接受 `title` 参数——Task 3 修复)

---

### Task 2b: 质量审查修复(输出目录检查 / 用法提示 / 路径规范化)

质量审查发现 spec「错误处理」表有两项未落实,补做(新增 1 个测试 + resolve_paths 小改):

**Files:**
- Modify: `md2html.py`(`resolve_paths`、`build_parser` 的 `-o` help)
- Modify: `test_md2html.py`(TestResolvePaths 新增 1 个用例)

- [ ] **Step 1: 新增测试** `TestResolvePaths.test_output_is_directory_returns_none`:

```python
    def test_output_is_directory_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / 'guide.md').write_text('# T', encoding='utf-8')
            sub = cwd / 'outdir'
            sub.mkdir()
            self.assertIsNone(md2html.resolve_paths(
                self._args(input='guide.md', output='outdir'), cwd=cwd))
```

- [ ] **Step 2: 修改 `resolve_paths`**:输入分支后对 `input_path`、`output_path` 应用 `.resolve()`(spec R1);`output_path` 计算完成后增加目录检查:

```python
    if output_path.is_dir():
        print(f"ERROR: {output_path} is a directory", file=sys.stderr)
        return None
```

输入不存在分支增加用法提示(仅无参模式):

```python
    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        if args.input is None:
            print("用法: md2html.py [input.md | 目录] [-o out.html] [--title T]", file=sys.stderr)
        return None
```

- [ ] **Step 3: `-o` help 文案**补充目录模式默认值说明:"(default: same name as the input with .html extension; README.html in directory mode)"

- [ ] **Step 4: 运行测试** → 预期 20 个用例:13 ok(TestResolvePaths 8 个),7 errors(仍为 convert() 的 TypeError,Task 3 修复)

---

### Task 3: convert() 模板动态化(标题/副标题/页脚)

**Files:**
- Modify: `md2html.py:115-137`(`convert` 函数开头与结尾)
- Modify: `md2html.py:153`(`<title>` 行)
- Modify: `md2html.py:584-587`(侧边栏 header)
- Modify: `md2html.py:591-593`(侧边栏 footer)

- [ ] **Step 1: 修改 convert() 签名与变量计算**

原内容(`md2html.py:115-117`):

```python
def convert(readme_path, output_path):
    md_text = Path(readme_path).read_text(encoding='utf-8')
```

替换为:

```python
def convert(input_path, output_path, title=None):
    input_path = Path(input_path)
    md_text = input_path.read_text(encoding='utf-8')

    if title is None:
        title = extract_first_h1(md_text) or input_path.stem
    title_html = html.escape(title)
    source_name = html.escape(input_path.name)
    footer_date = datetime.now().strftime('%Y-%m')
```

- [ ] **Step 2: 模板 `<title>` 动态化**

原内容(`md2html.py:153`):

```python
<title>Autogen — GT SDK Code Generation Engineer's Guide</title>
```

替换为:

```python
<title>{title_html}</title>
```

- [ ] **Step 3: 侧边栏 header 动态化**

原内容(`md2html.py:584-587`):

```python
    <div class="sidebar-header">
        <h2>Autogen</h2>
        <div class="subtitle">GT SDK Code Generator</div>
    </div>
```

替换为:

```python
    <div class="sidebar-header">
        <h2>{title_html}</h2>
        <div class="subtitle">{source_name}</div>
    </div>
```

- [ ] **Step 4: 侧边栏 footer 动态化**

原内容(`md2html.py:591-593`):

```python
    <div class="sidebar-footer">
        v2.0 &middot; Auto-generated from README.md &middot; 2026-08
    </div>
```

替换为:

```python
    <div class="sidebar-footer">
        Auto-generated from {source_name} &middot; {footer_date}
    </div>
```

- [ ] **Step 5: 确认 convert() 末尾写入逻辑不变**

保持原样(无需改动):

```python
    Path(output_path).write_text(html_template, encoding='utf-8')
    print(f"[OK] Generated: {output_path}")
    print(f"     Size: {len(html_template):,} bytes")
    print(f"     TOC entries: {toc_html.count('<li')}")
```

- [ ] **Step 6: 运行全部测试**

Run: `python -m unittest test_md2html -v`
Expected: 全部 PASS(共 20 个用例)

---

### Task 4: 启动脚本 md2html.bat / md2html.sh

**Files:**
- Create: `md2html.bat`
- Create: `md2html.sh`

- [ ] **Step 1: 创建 md2html.bat**

完整内容(注意:文件必须是 CRLF 或 LF 均可,copy 时不要引入 BOM):

```bat
@echo off
setlocal
set "SCRIPT=%~dp0md2html.py"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%SCRIPT%" %*
    exit /b %errorlevel%
)
where python >nul 2>nul
if not errorlevel 1 (
    python "%SCRIPT%" %*
    exit /b %errorlevel%
)
where python3 >nul 2>nul
if not errorlevel 1 (
    python3 "%SCRIPT%" %*
    exit /b %errorlevel%
)
echo ERROR: Python 3 not found. Please install Python 3.8+ and add it to PATH. 1>&2
exit /b 1
```

- [ ] **Step 2: 创建 md2html.sh**

完整内容:

```sh
#!/usr/bin/env sh
# Convert Markdown to HTML. Usage: ./md2html.sh [input.md] [-o output.html] [--title T]
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCRIPT="$SCRIPT_DIR/md2html.py"

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$SCRIPT" "$@"
else
    echo "ERROR: Python 3 not found. Please install Python 3.8+." >&2
    exit 1
fi
```

- [ ] **Step 3: 赋予 sh 执行权限**

Run: `chmod +x md2html.sh && ls -l md2html.sh`
Expected: 权限含 `x`(如 `-rwxr-xr-x`)

- [ ] **Step 4: sh 语法检查**

Run: `bash -n md2html.sh`
Expected: 无输出,退出码 0

- [ ] **Step 5: 用 bat 实际转换验证(cmd)**

Run: `cmd //c md2html.bat md2html工具说明.md -o _verify_bat.html`
Expected: 输出 `[OK] Generated: ...`,生成 `_verify_bat.html`

- [ ] **Step 6: 用 sh 实际转换验证(Git Bash)**

Run: `./md2html.sh md2html工具说明.md -o _verify_sh.html`
Expected: 输出 `[OK] Generated: ...`,生成 `_verify_sh.html`

- [ ] **Step 7: 对比两个输出并清理**

Run: `cmp _verify_bat.html _verify_sh.html && rm _verify_bat.html _verify_sh.html`
Expected: `cmp` 无输出(文件一致),临时文件已删除

---

### Task 5: 更新文档 md2html工具说明.md

**Files:**
- Modify: `md2html工具说明.md`(全文重写)

- [ ] **Step 1: 用以下完整内容重写文档**

```markdown
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

(Pygments 用于代码高亮;新版本 `markdown` 自带 lexers,缺 Pygments 时仍可工作,建议安装。)

### Windows

```bat
:: 双击或命令行运行(自动查找 Python)
md2html.bat

:: 等价于
python md2html.py

:: 转换任意文件
md2html.bat 文档.md -o 输出\文档.html
```

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
| `Ctrl+\` | 切换侧边栏(桌面端也支持) |
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

这样生成的 TOC 与 markdown toc 扩展完全一致,但更可控(可排除特定章节、调整深度等)。

### 跨平台兼容

- 路径处理统一使用 `pathlib`,Windows `\` 与 Linux `/` 自动适配
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
```

- [ ] **Step 2: 用工具自身转换文档,验证文档可正常转换**

Run: `python md2html.py md2html工具说明.md`
Expected: 输出 `[OK] Generated: md2html工具说明.html`,无报错;用浏览器打开确认中文渲染、TOC、代码高亮正常(转换产物保留,可自行删除)

---

### Task 6: 手工验证清单(对应 spec「测试与验证」)

**Files:** 无代码改动

- [ ] **Step 1: 准备临时验证文件**

Run: `printf '# 验证标题\n\n## 章节一\n\n正文\n\n```python\nprint("hi")\n```\n' > _tmp_verify.md`
Expected: 生成 `_tmp_verify.md`

- [ ] **Step 2: 逐项验证**

| # | 命令 | 预期 |
|---|------|------|
| 1 | `python md2html.py _tmp_verify.md` | 生成 `_tmp_verify.html`,`<title>` 为「验证标题」 |
| 2 | `python md2html.py _tmp_verify.md -o _tmp_out/deep/verify.html` | 自动建 `_tmp_out/deep/` 并生成 |
| 3 | `python md2html.py --title "自定义" _tmp_verify.md -o _tmp_verify2.html` | 标题为「自定义」 |
| 4 | `python md2html.py _does_not_exist.md; echo "exit=$?"` | 输出 `ERROR: ... not found`,`exit=1` |
| 5 | `python -m unittest test_md2html -v` | 全部 PASS |
| 6 | `bash -n md2html.sh` | 无输出 |
| 7 | `cmd //c md2html.bat _tmp_verify.md -o _tmp_verify3.html` | 生成成功 |

- [ ] **Step 3: 浏览器检查生成的 HTML**

用浏览器打开 `_tmp_verify.html` / `md2html工具说明.html`,检查:
- 侧边栏 TOC 层级与章节编号正确
- 滚动时导航高亮跟随
- 代码块 Pygments 高亮、明暗主题切换正常
- 移动端窗口宽度(≤900px)汉堡菜单正常

- [ ] **Step 4: 清理临时文件**

Run: `rm -f _tmp_verify.md _tmp_verify.html _tmp_verify2.html _tmp_verify3.html && rm -rf _tmp_out`
Expected: 临时文件已删除(保留 `md2html工具说明.html` 与否由用户决定)

---

## Self-Review 记录

- **Spec 覆盖:** R1(多模式 CLI)→ Task 2 `build_parser`/`resolve_paths`/`main`;R2(标题日期动态化)→ Task 1 测试 + Task 3 模板变量;R3(平台兼容)→ Task 2 `_setup_console_encoding` + Task 5 文档;R4(启动脚本)→ Task 4;R5(文档更新)→ Task 5。spec 测试清单 → Task 6。无遗漏。
- **占位符扫描:** 所有代码步骤均为完整内容,无 TBD/TODO。
- **类型一致性:** `resolve_paths` 返回三元组 `(input_path, output_path, title)` 或 `None`,Task 2 定义与 Task 1 测试断言一致;`convert(input_path, output_path, title=None)` 在 Task 2 `main` 调用与 Task 3 定义一致;`extract_first_h1` 返回 `str | None`,测试覆盖两种分支。
