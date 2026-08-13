# md2html 无依赖化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除 `markdown`/`pygments` 依赖,用纯 Python 标准库实现 Markdown→HTML 转换器与轻量代码高亮器。

**Architecture:** 在 `md2html.py` 内新增 `markdown_to_html()`(块级解析 + 行内解析)与 `highlight_code()`(正则 token 高亮,输出 Pygments 同款 CSS 类),替换 `convert()` 中的 markdown 库调用;现有后处理管线、模板 CSS/JS、CLI、launchers 零改动。

**Tech Stack:** Python 3.8+ 标准库(re/hmtl/pathlib/argparse/unittest),无第三方依赖

**Spec:** `docs/superpowers/specs/2026-08-13-md2html-dependency-free-design.md`

**仓库:** 已是 git 仓库(main 分支),每个任务末尾提交。
**测试运行命令:** `python -m unittest test_md2html -v`(本机 Windows,Git Bash)
**零依赖验证:** `python -S`(跳过 site-packages,仅标准库)

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `test_md2html.py` | 修改 | 新增 `TestConverter` 类(28 个用例) |
| `md2html.py` | 修改 | 新增转换器/高亮器,替换依赖调用 |
| `md2html工具说明.md` + `.html` | 修改 | 依赖/技术实现章节更新,重新生成 |

## 新函数接口约定(全计划一致)

```python
_escape_html(text: str) -> str                    # & < > " 转义
_render_inline(text: str) -> str                  # 行内 markdown → HTML
markdown_to_html(md_text: str) -> str             # 完整块级+行内转换
highlight_code(code: str, lang: str) -> str       # 高亮(已转义 + span),未知语言纯转义
_parse_list(lines, i) -> (html, next_i)           # 列表递归解析
_parse_table(lines, i) -> (html, next_i)          # GFM 表格解析
_split_cells(line) -> [str]                       # 表格行切单元格
_build_hl_regex(spec) -> re.Pattern               # 语言 spec → 组合正则
_highlight_line(line, cre) -> str                 # 单行 token 扫描
```

代码块输出结构(固定):`<div class="highlight"><pre><code class="language-lang">…</code></pre></div>`(无语言时无 class)。

---

### Task 1: TestConverter 失败测试(RED)

**Files:**
- Modify: `test_md2html.py`(在 `TestBatch` 类之前插入新类)

- [ ] **Step 1: 插入测试类**

在 `test_md2html.py` 中 `class TestBatch(unittest.TestCase):` 之前插入以下完整代码:

```python
class TestConverter(unittest.TestCase):
    def _conv(self, md):
        return md2html.markdown_to_html(md)

    # ---- 块级 ----
    def test_headings(self):
        self.assertIn('<h1>Title</h1>', self._conv('# Title'))
        self.assertIn('<h2>Sec</h2>', self._conv('## Sec'))
        self.assertIn('<h6>X</h6>', self._conv('###### X'))

    def test_heading_with_inline(self):
        self.assertEqual('<h2>你好 <code>世界</code></h2>', self._conv('## 你好 `世界`'))

    def test_paragraph_with_br(self):
        self.assertEqual('<p>a<br>b</p>', self._conv('a\nb'))

    def test_two_paragraphs(self):
        self.assertEqual('<p>a</p>\n<p>b</p>', self._conv('a\n\nb'))

    def test_hr(self):
        self.assertEqual('<hr>', self._conv('---'))

    def test_fenced_code_with_lang(self):
        html = self._conv('```python\nprint("hi")\n```')
        self.assertIn('<div class="highlight"><pre><code class="language-python">', html)
        self.assertIn('<span class="nb">print</span>', html)
        self.assertIn('<span class="s1">&quot;hi&quot;</span>', html)

    def test_fenced_code_no_lang(self):
        html = self._conv('```\nplain <text>\n```')
        self.assertIn('<div class="highlight"><pre><code>', html)
        self.assertIn('plain &lt;text&gt;', html)
        self.assertNotIn('class="language', html)

    def test_tilde_fence(self):
        self.assertIn('<pre><code class="language-bash">', self._conv('~~~bash\nls\n~~~'))

    def test_table(self):
        html = self._conv('| a | b |\n|---|---|\n| 1 | 2 |')
        self.assertIn('<table>', html)
        self.assertIn('<th>a</th>', html)
        self.assertIn('<td>1</td>', html)
        self.assertIn('<tbody>', html)

    def test_table_with_inline(self):
        html = self._conv('| a |\n|---|\n| `x` |')
        self.assertIn('<td><code>x</code></td>', html)

    def test_blockquote(self):
        self.assertEqual('<blockquote>\n<p>note</p>\n</blockquote>', self._conv('> note'))

    def test_blockquote_multiline(self):
        html = self._conv('> a\n> b')
        self.assertIn('<blockquote>', html)
        self.assertIn('a<br>b', html)

    def test_unordered_list(self):
        self.assertEqual('<ul>\n<li>a</li>\n<li>b</li>\n</ul>\n', self._conv('- a\n- b'))

    def test_ordered_list(self):
        html = self._conv('1. a\n2. b')
        self.assertIn('<ol>', html)
        self.assertIn('<li>a</li>', html)

    def test_nested_list(self):
        html = self._conv('- a\n  - b\n- c')
        self.assertEqual(html.count('<ul>'), 2)
        self.assertIn('<li>a<ul>', html)

    def test_empty_document(self):
        self.assertEqual('', self._conv(''))

    def test_paragraph_stops_at_heading(self):
        self.assertEqual('<p>a</p>\n<h2>B</h2>', self._conv('a\n## B'))

    # ---- 行内 ----
    def test_inline_escaping(self):
        self.assertEqual('<p>a &lt; b &amp; &quot;q&quot;</p>', self._conv('a < b & "q"'))

    def test_bold_italic(self):
        self.assertEqual('<p><strong>b</strong> <em>i</em></p>', self._conv('**b** *i*'))

    def test_underscore_italic_not_in_word(self):
        self.assertEqual('<p>foo_bar_baz</p>', self._conv('foo_bar_baz'))

    def test_link(self):
        self.assertEqual('<p><a href="https://x.test">t</a></p>',
                         self._conv('[t](https://x.test)'))

    def test_image(self):
        self.assertEqual('<p><img src="i.png" alt="alt"></p>', self._conv('![alt](i.png)'))

    def test_inline_html_passthrough(self):
        self.assertEqual('<p>a<br>b</p>', self._conv('a<br>b'))

    def test_link_text_with_formatting(self):
        self.assertEqual('<p><a href="u">x <strong>y</strong></a></p>',
                         self._conv('[x **y**](u)'))

    # ---- 高亮器 ----
    def test_highlight_unknown_lang_plain(self):
        self.assertEqual('a &lt; b', md2html.highlight_code('a < b', 'nolang'))

    def test_highlight_python_tokens(self):
        html = md2html.highlight_code('# comment\nx = 42', 'python')
        self.assertIn('<span class="c1"># comment</span>', html)
        self.assertIn('<span class="mi">42</span>', html)

    def test_highlight_bash_variable(self):
        html = md2html.highlight_code('echo $HOME', 'bash')
        self.assertIn('<span class="nb">echo</span>', html)
        self.assertIn('<span class="nv">$HOME</span>', html)

    def test_highlight_sql_keywords(self):
        html = md2html.highlight_code("SELECT * FROM t WHERE x = 'v'", 'sql')
        self.assertIn('<span class="k">SELECT</span>', html)
        self.assertIn('<span class="s1">\'v\'</span>', html)
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest test_md2html.TestConverter -v`
Expected: 28 个用例全部 ERROR:`AttributeError: module 'md2html' has no attribute 'markdown_to_html'`(及 `highlight_code`)

- [ ] **Step 3: 提交**

```bash
git add test_md2html.py
git commit -m "test: 新增 TestConverter 无依赖转换器失败测试(28 用例)"
```

---

### Task 2: 行内 + 块级解析器(GREEN 第一部分)

**Files:**
- Modify: `md2html.py`(在 `extract_first_h1` 函数之后插入)

- [ ] **Step 1: 插入解析器代码**

在 `md2html.py` 中 `extract_first_h1` 函数定义结束(`return None`)之后、`def build_heading_index` 之前,插入以下完整代码:

```python
# ------------------------------------------------------------
# Markdown -> HTML converter (standard library only)
# ------------------------------------------------------------
_INLINE_RE = re.compile(
    r'(</?[A-Za-z][^>\n]*>)'          # raw inline HTML passthrough
    r'|(!\[[^\]]*\]\([^)\s]+\))'      # image
    r'|(\[[^\]]+\]\([^)\s]+\))'       # link
    r'|(`[^`\n]+`)'                   # code span
    r'|(\*\*[^*\n]+\*\*)'             # bold
    r'|(\*[^*\n]+\*)'                 # italic (asterisk)
    r'|((?<!\w)_[^_\n]+_(?!\w))'      # italic (underscore, word-bounded)
)
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
_FENCE_RE = re.compile(r'^\s{0,3}(`{3,}|~{3,})\s*(.*)$')
_HR_RE = re.compile(r'^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$')
_LIST_RE = re.compile(r'^(\s*)([-*+]|\d+[.)])\s+(.*)$')
_TABLE_DELIM_RE = re.compile(
    r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$')


def _escape_html(text):
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))


def _render_inline(text):
    out = []
    for tok in _INLINE_RE.split(text):
        if not tok:
            continue
        m = re.fullmatch(r'</?[A-Za-z][^>\n]*>', tok)
        if m:
            out.append(tok)
            continue
        m = re.fullmatch(r'!\[([^\]]*)\]\(([^)\s]+)\)', tok)
        if m:
            out.append(f'<img src="{_escape_html(m.group(2))}" '
                       f'alt="{_escape_html(m.group(1))}">')
            continue
        m = re.fullmatch(r'\[([^\]]+)\]\(([^)\s]+)\)', tok)
        if m:
            out.append(f'<a href="{_escape_html(m.group(2))}">'
                       f'{_render_inline(m.group(1))}</a>')
            continue
        m = re.fullmatch(r'`([^`\n]+)`', tok)
        if m:
            out.append('<code>' + _escape_html(m.group(1)) + '</code>')
            continue
        m = re.fullmatch(r'\*\*([^*\n]+)\*\*', tok)
        if m:
            out.append('<strong>' + _render_inline(m.group(1)) + '</strong>')
            continue
        m = re.fullmatch(r'\*([^*\n]+)\*', tok)
        if m:
            out.append('<em>' + _render_inline(m.group(1)) + '</em>')
            continue
        m = re.fullmatch(r'(?<!\w)_([^_\n]+)_(?!\w)', tok)
        if m:
            out.append('<em>' + _render_inline(m.group(1)) + '</em>')
            continue
        out.append(_escape_html(tok))
    return ''.join(out)


def highlight_code(code, lang):
    """Highlight code for the given language; unknown language -> escaped
    plain text. (Full tokenizer lands in Task 3.)"""
    return _escape_html(code)


def markdown_to_html(md_text):
    lines = md_text.split('\n')
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        hm = _HEADING_RE.match(line)
        if hm:
            level = len(hm.group(1))
            title = re.sub(r'\s+#+\s*$', '', hm.group(2)).strip()
            out.append(f'<h{level}>{_render_inline(title)}</h{level}>')
            i += 1
            continue
        fm = _FENCE_RE.match(line)
        if fm and len(fm.group(1)) >= 3:
            fence_char = fm.group(1)[0]
            lang = fm.group(2).strip()
            i += 1
            buf = []
            close_re = re.compile(r'^\s{0,3}' + re.escape(fence_char) + r'{3,}\s*$')
            while i < n and not close_re.match(lines[i]):
                buf.append(lines[i])
                i += 1
            if i < n:
                i += 1
            code = '\n'.join(buf)
            lang_class = f' class="language-{lang}"' if lang else ''
            out.append(f'<div class="highlight"><pre><code{lang_class}>'
                       f'{highlight_code(code, lang)}</code></pre></div>')
            continue
        if _HR_RE.match(line):
            out.append('<hr>')
            i += 1
            continue
        if line.strip().startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(re.sub(r'^\s{0,3}>\s?', '', lines[i]))
                i += 1
            out.append('<blockquote>\n' + markdown_to_html('\n'.join(buf))
                       + '\n</blockquote>')
            continue
        lm = _LIST_RE.match(line)
        if lm:
            html, i = _parse_list(lines, i)
            out.append(html)
            continue
        if '|' in line and i + 1 < n and _TABLE_DELIM_RE.match(lines[i + 1]):
            html, i = _parse_table(lines, i)
            out.append(html)
            continue
        buf = [line]
        i += 1
        while i < n and lines[i].strip():
            if (_HEADING_RE.match(lines[i]) or _FENCE_RE.match(lines[i])
                    or _HR_RE.match(lines[i]) or _LIST_RE.match(lines[i])
                    or lines[i].strip().startswith('>')):
                break
            if ('|' in lines[i] and i + 1 < n
                    and _TABLE_DELIM_RE.match(lines[i + 1])):
                break
            buf.append(lines[i])
            i += 1
        out.append('<p>' + '<br>'.join(_render_inline(b) for b in buf) + '</p>')
    return '\n'.join(out)


def _parse_list(lines, i):
    """Parse one list starting at lines[i]; returns (html, next_index)."""
    first = _LIST_RE.match(lines[i])
    indent = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    tag = 'ol' if ordered else 'ul'
    n = len(lines)
    out = [f'<{tag}>\n']
    while i < n:
        m = _LIST_RE.match(lines[i])
        if (not m or len(m.group(1)) != indent
                or ordered != m.group(2)[0].isdigit()):
            break
        content = [m.group(3)]
        i += 1
        sub_html = ''
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                break
            lm = _LIST_RE.match(line)
            if lm and len(lm.group(1)) <= indent:
                break
            if lm and len(lm.group(1)) > indent:
                sub_html, i = _parse_list(lines, i)
                continue
            content.append(line[indent:] if len(line) > indent else line.lstrip())
            i += 1
        out.append(_render_list_item(content, sub_html))
    out.append(f'</{tag}>\n')
    return ''.join(out), i


def _render_list_item(content, sub_html):
    text = '\n'.join(content).strip('\n')
    if '\n' not in text:
        return f'<li>{_render_inline(text)}{sub_html}</li>\n'
    return f'<li>{markdown_to_html(text)}{sub_html}</li>\n'


def _parse_table(lines, i):
    header = _split_cells(lines[i])
    i += 2  # skip header + delimiter row
    rows = []
    n = len(lines)
    while i < n and lines[i].strip() and '|' in lines[i]:
        rows.append(_split_cells(lines[i]))
        i += 1
    thead = ('<thead>\n<tr>\n'
             + ''.join(f'<th>{_render_inline(c)}</th>\n' for c in header)
             + '</tr>\n</thead>\n')
    tbody = ('<tbody>\n'
             + ''.join('<tr>\n'
                       + ''.join(f'<td>{_render_inline(c)}</td>\n' for c in row)
                       + '</tr>\n' for row in rows)
             + '</tbody>\n')
    return f'<table>\n{thead}{tbody}</table>\n', i


def _split_cells(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [c.strip() for c in line.split('|')]
```

- [ ] **Step 2: 运行测试**

Run: `python -m unittest test_md2html.TestConverter -v`
Expected: 24 个解析/行内用例 PASS;**4 个高亮 token 用例仍失败**(`test_fenced_code_with_lang`、`test_highlight_python_tokens`、`test_highlight_bash_variable`、`test_highlight_sql_keywords`——`highlight_code` 尚为纯转义 stub,Task 3 实现)

- [ ] **Step 3: 全量回归**

Run: `python -m unittest test_md2html -v`
Expected: 原 32 个用例全部 PASS,总计 24 ok + 4 errors(高亮 4 个)

- [ ] **Step 4: 提交**

```bash
git add md2html.py
git commit -m "feat: 纯标准库 markdown 解析器(块级+行内,高亮暂为纯文本)"
```

---

### Task 3: 轻量高亮器(GREEN 第二部分)

**Files:**
- Modify: `md2html.py`(替换 Task 2 的 `highlight_code` stub,并在其后插入语言表与扫描器)

- [ ] **Step 1: 替换 highlight_code 并插入高亮器完整实现**

将 Task 2 插入的 stub:

```python
def highlight_code(code, lang):
    """Highlight code for the given language; unknown language -> escaped
    plain text. (Full tokenizer lands in Task 3.)"""
    return _escape_html(code)
```

整体替换为以下完整代码:

```python
_HL_ALIASES = {
    'py': 'python', 'python3': 'python',
    'sh': 'bash', 'shell': 'bash', 'zsh': 'bash',
    'c++': 'cpp', 'cxx': 'cpp', 'cc': 'cpp',
    'js': 'javascript', 'ts': 'javascript',
    'yml': 'yaml',
    'cmd': 'bat', 'dosbatch': 'bat',
    'xml': 'html',
}

_HL_SPECS = {
    'python': {
        'comment': r'#[^\n]*',
        'strings': [
            r'(?:[rbfu]{0,2})"(?:[^"\\\n]|\\.)*"',
            r"(?:[rbfu]{0,2})'(?:[^'\\\n]|\\.)*'",
            r'(?:[rbfu]{0,2})"""(?:[^"\\]|\\[\s\S]|"(?!""))*"""',
            r"(?:[rbfu]{0,2})'''(?:[^'\\]|\\[\s\S]|'(?!''))*'''",
        ],
        'keywords': ['def', 'class', 'return', 'if', 'elif', 'else', 'for',
                     'while', 'in', 'not', 'and', 'or', 'import', 'from', 'as',
                     'try', 'except', 'finally', 'raise', 'with', 'lambda',
                     'yield', 'pass', 'break', 'continue', 'global', 'nonlocal',
                     'del', 'assert', 'is', 'None', 'True', 'False', 'async',
                     'await'],
        'builtins': ['print', 'len', 'range', 'str', 'int', 'float', 'list',
                     'dict', 'set', 'tuple', 'bool', 'type', 'open', 'input',
                     'sum', 'min', 'max', 'sorted', 'enumerate', 'zip', 'map',
                     'filter', 'any', 'all', 'isinstance', 'issubclass',
                     'super', 'self'],
        'decorator': r'@[\w.]+',
    },
    'bash': {
        'comment': r'#[^\n]*',
        'strings': [r'"(?:[^"\\\n]|\\.)*"', r"'(?:[^'\\\n]|\\.)*'"],
        'keywords': ['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do',
                     'done', 'case', 'esac', 'in', 'function', 'local',
                     'export', 'return', 'exit'],
        'builtins': ['echo', 'cd', 'ls', 'grep', 'sed', 'awk', 'cat', 'mkdir',
                     'rm', 'cp', 'mv', 'chmod', 'chown', 'printf', 'source',
                     'set', 'unset', 'readonly', 'read', 'true', 'false',
                     'command', 'exec', 'which', 'find', 'xargs', 'curl',
                     'wget', 'tar', 'sudo', 'pip', 'python', 'python3', 'git'],
        'variable': r'\$[\w{}]+',
    },
    'yaml': {
        'comment': r'#[^\n]*',
        'strings': [r'"(?:[^"\\\n]|\\.)*"', r"'(?:[^'\\\n]|\\.)*'"],
        'keywords': ['true', 'false', 'null', 'yes', 'no'],
        'variable': r'^[\s\-]*[\w.-]+(?=\s*:)',
    },
    'json': {
        'strings': [r'"(?:[^"\\\n]|\\.)*"'],
        'keywords': ['true', 'false', 'null'],
    },
    'sql': {
        'comment': r'--[^\n]*',
        'strings': [r"'(?:[^'\\\n]|\\.)*'", r'"(?:[^"\\\n]|\\.)*"'],
        'keywords': ['SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES',
                     'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'DROP',
                     'ALTER', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON',
                     'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'AND', 'OR',
                     'NOT', 'NULL', 'AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG',
                     'MIN', 'MAX', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES',
                     'INDEX', 'UNIQUE', 'DEFAULT', 'INT', 'VARCHAR', 'TEXT',
                     'IF', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'],
        'funcs': False,
    },
    'c': {
        'comment': r'//[^\n]*',
        'strings': [r'"(?:[^"\\\n]|\\.)*"', r"'(?:[^'\\\n]|\\.)*'"],
        'keywords': ['int', 'char', 'float', 'double', 'void', 'return', 'if',
                     'else', 'for', 'while', 'do', 'switch', 'case', 'break',
                     'continue', 'struct', 'typedef', 'const', 'static',
                     'unsigned', 'long', 'short', 'sizeof', 'enum', 'union',
                     'extern', 'volatile', 'register', 'signed', 'goto',
                     'NULL'],
    },
    'cpp': {
        'comment': r'//[^\n]*',
        'strings': [r'"(?:[^"\\\n]|\\.)*"', r"'(?:[^'\\\n]|\\.)*'"],
        'keywords': ['int', 'char', 'float', 'double', 'void', 'return', 'if',
                     'else', 'for', 'while', 'do', 'switch', 'case', 'break',
                     'continue', 'struct', 'typedef', 'const', 'static',
                     'unsigned', 'long', 'short', 'sizeof', 'enum', 'union',
                     'extern', 'volatile', 'register', 'signed', 'class',
                     'public', 'private', 'protected', 'namespace', 'template',
                     'typename', 'new', 'delete', 'this', 'virtual', 'override',
                     'using', 'bool', 'true', 'false', 'auto', 'nullptr',
                     'try', 'catch', 'throw', 'constexpr'],
    },
    'javascript': {
        'comment': r'//[^\n]*',
        'strings': [r'"(?:[^"\\\n]|\\.)*"', r"'(?:[^'\\\n]|\\.)*'",
                    r'`(?:[^`\\\n]|\\.)*`'],
        'keywords': ['var', 'let', 'const', 'function', 'return', 'if', 'else',
                     'for', 'while', 'do', 'switch', 'case', 'break',
                     'continue', 'class', 'new', 'this', 'typeof',
                     'instanceof', 'import', 'export', 'from', 'async',
                     'await', 'try', 'catch', 'finally', 'throw', 'true',
                     'false', 'null', 'undefined', 'delete', 'in', 'of',
                     'extends', 'super', 'default'],
    },
    'bat': {
        'comment': r'(?i)::[^\n]*|(?i)rem\s[^\n]*',
        'strings': [r'"(?:[^"\\\n]|\\.)*"'],
        'keywords': ['echo', 'set', 'if', 'else', 'for', 'goto', 'call', 'exit',
                     'setlocal', 'endlocal', 'where', 'errorlevel', 'in', 'do',
                     'not', 'pause', 'findstr', 'start', 'shift', 'pushd',
                     'popd'],
        'variable': r'%[^%\n]*%',
    },
    'html': {
        'comment': r'<!--[\s\S]*?-->',
        'strings': [r'"[^"\n]*"', r"'[^'\n]*'"],
        'tag': r'</?[A-Za-z][^>\n]*>',
        'keywords': ['DOCTYPE', 'html', 'head', 'body', 'meta', 'title', 'link',
                     'script', 'style', 'div', 'span', 'p', 'a', 'img', 'ul',
                     'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
                     'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'pre',
                     'code', 'button', 'form', 'input', 'label', 'nav', 'main',
                     'aside', 'header', 'footer', 'section', 'article',
                     'strong', 'em', 'blockquote'],
    },
}


def _build_hl_regex(spec):
    parts = []
    if 'comment' in spec:
        parts.append(r'(?P<c>%s)' % spec['comment'])
    for idx, s in enumerate(spec.get('strings', [])):
        parts.append(r'(?P<s%d>%s)' % (idx, s))
    if spec.get('keywords'):
        parts.append(r'(?P<k>\b(?:%s)\b)'
                     % '|'.join(sorted(spec['keywords'], key=len, reverse=True)))
    if spec.get('builtins'):
        parts.append(r'(?P<b>\b(?:%s)\b)'
                     % '|'.join(sorted(spec['builtins'], key=len, reverse=True)))
    if spec.get('variable'):
        parts.append(r'(?P<v>%s)' % spec['variable'])
    if spec.get('decorator'):
        parts.append(r'(?P<d>%s)' % spec['decorator'])
    if spec.get('tag'):
        parts.append(r'(?P<t>%s)' % spec['tag'])
    parts.append(r'(?P<m>\b\d+(?:\.\d+)?\b)')
    if spec.get('funcs', True):
        parts.append(r'(?P<f>\b\w+(?=\())')
    return re.compile('|'.join(parts))


_HL_CLASSES = {'c': 'c1', 'k': 'k', 'b': 'nb', 'm': 'mi',
               'f': 'nf', 'd': 'nf', 'v': 'nv', 't': 'nc'}


def _highlight_line(line, cre):
    out = []
    pos = 0
    for m in cre.finditer(line):
        if m.start() > pos:
            out.append(_escape_html(line[pos:m.start()]))
        g = m.lastgroup
        if g and g[0] == 's':
            cls = 's1' if g[-1] in '02' else 's2'
        else:
            cls = _HL_CLASSES[g[0]]
        out.append(f'<span class="{cls}">{_escape_html(m.group())}</span>')
        pos = m.end()
    if pos < len(line):
        out.append(_escape_html(line[pos:]))
    return ''.join(out)


def highlight_code(code, lang):
    """Highlight code for the given language; unknown language -> escaped
    plain text. Always escapes input (XSS-safe)."""
    key = (lang or '').lower()
    spec = _HL_SPECS.get(_HL_ALIASES.get(key, key))
    if spec is None:
        return _escape_html(code)
    try:
        cre = _build_hl_regex(spec)
        return '\n'.join(_highlight_line(line, cre) for line in code.split('\n'))
    except Exception:
        return _escape_html(code)
```

- [ ] **Step 2: 运行测试**

Run: `python -m unittest test_md2html -v`
Expected: **60/60 全部 PASS**(32 旧 + 28 新)

- [ ] **Step 3: 提交**

```bash
git add md2html.py
git commit -m "feat: 内置轻量代码高亮器(10 种语言,输出 Pygments 同款 CSS 类)"
```

---

### Task 4: 集成替换依赖(GREEN 收尾)

**Files:**
- Modify: `md2html.py`(顶部 import、docstring、convert() 内 markdown 调用)

- [ ] **Step 1: 顶部 import 与 docstring**

原内容(文件 1-13 行):

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

替换为:

```python
#!/usr/bin/env python3
"""
Convert a Markdown file into a standalone HTML page with sidebar TOC navigation.
Zero dependencies - Python standard library only.
"""
import argparse
import html
import re
import sys
from datetime import datetime
from pathlib import Path
```

- [ ] **Step 2: convert() 内替换 markdown 库调用**

原内容(convert() 中约 155-173 行):

```python
    # Convert markdown to HTML with extensions
    extensions = [
        'fenced_code',
        'tables',
        'codehilite',
        'nl2br',
        'sane_lists',
    ]
    ext_configs = {
        'codehilite': {
            'css_class': 'highlight',
            'guess_lang': True,
        },
    }
    md = markdown.Markdown(extensions=extensions, extension_configs=ext_configs)
    body_html = md.convert(md_text)
```

替换为:

```python
    # Convert markdown to HTML (stdlib converter)
    body_html = markdown_to_html(md_text)
```

- [ ] **Step 3: 全量测试**

Run: `python -m unittest test_md2html -v`
Expected: 60/60 全部 PASS

- [ ] **Step 4: 零依赖验证**

Run: `python -S -m unittest test_md2html 2>&1 | tail -3`
Expected: `Ran 60 tests` / `OK`(-S 跳过 site-packages,证明纯标准库可运行)

Run: `python -S md2html.py "md2html工具说明.md" 2>&1 | head -1`
Expected: `[OK] Generated: ...md2html工具说明.html`(注意:此步会先按旧文档内容重新生成 HTML,Task 5 会再次生成)

Run: `grep -n "^import markdown\|^import pygments\|from markdown\|from pygments" md2html.py`
Expected: 无输出(无任何第三方导入)

- [ ] **Step 5: 提交**

```bash
git add md2html.py
git commit -m "feat: convert() 改用自研转换器,移除 markdown/pygments 依赖"
```

---

### Task 5: 文档更新与最终验证

**Files:**
- Modify: `md2html工具说明.md`(四处更新)+ 重新生成 HTML

- [ ] **Step 1: 概述补充零依赖**

原文:

```markdown
- 单文件工具,拷贝即用,无需安装
- 生成的 HTML 可离线使用——CSS 和 JavaScript 全部内嵌
- 跨平台:Windows / Linux / macOS 均可运行,附 `md2html.bat` / `md2html.sh` 启动脚本
```

替换为:

```markdown
- 单文件工具,拷贝即用,**零第三方依赖**(纯 Python 标准库,无需 pip install)
- 生成的 HTML 可离线使用——CSS 和 JavaScript 全部内嵌
- 跨平台:Windows / Linux / macOS 均可运行,附 `md2html.bat` / `md2html.sh` 启动脚本
```

- [ ] **Step 2: 快速开始「安装依赖」小节整体替换**

原文:

```markdown
### 安装依赖

```bash
pip install markdown pygments
```

(Pygments 用于代码高亮;缺 Pygments 时代码块不高亮,但转换仍可正常工作,建议安装。)

> **注意:** `md2html.bat` 优先使用 `py -3` 启动器。若 `py -3` 与 `python` 指向不同的解释器,请确认 `py -3` 对应的 Python 也已安装依赖,否则会报 `ModuleNotFoundError: No module named 'markdown'`。
```

替换为:

```markdown
### 环境要求

**无需安装任何第三方依赖**——仅需 Python 3.8+(Markdown 解析与代码高亮均为内置实现,不会再出现 `No module named markdown` 报错)。
```

- [ ] **Step 3: 依赖表替换**

原文:

```markdown
| 依赖 | 安装 | 说明 |
|------|------|------|
| Python | 3.8+ | Windows:python.org 安装并勾选 "Add to PATH" |
| markdown | `pip install markdown` | Markdown 解析 |
| Pygments | `pip install pygments` | 代码高亮(推荐安装) |
```

替换为:

```markdown
| 依赖 | 说明 |
|------|------|
| Python | 3.8+(唯一要求,Windows:python.org 安装并勾选 "Add to PATH") |
| 第三方库 | 无(Markdown 解析与代码高亮均为内置实现) |
```

- [ ] **Step 4: 代码块特性说明与对比表更新**

原文(代码块小节第一行):

```markdown
- 使用 **Pygments** 进行语法高亮
- 自动检测语言(bash / yaml / c / python / jinja2 等)
```

替换为:

```markdown
- 使用**内置轻量高亮器**(标准库正则实现)进行语法高亮
- 按围栏语言标签高亮(python / bash / yaml / json / sql / c / cpp / js / bat / html 等,未知语言纯文本)
```

原文(对比表行):

```markdown
| md2html.py | 单 HTML 文件 | 侧边栏 TOC + 滚动追踪 | Pygments | ✅ |
```

替换为:

```markdown
| md2html.py | 单 HTML 文件 | 侧边栏 TOC + 滚动追踪 | 内置轻量 | ✅ |
```

- [ ] **Step 5: 处理流程图更新**

原文(处理流程代码块中):

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
```

替换为:

```
输入 .md 文件(默认 README.md)
    │
    ▼ 标题提取:--title > 第一个 h1 > 文件名
    ▼ 内置解析器(纯标准库,零依赖)
    │  ├─ 块级:标题/段落/围栏代码/表格/引用/列表/hr
    │  ├─ 行内:粗斜体/行内代码/链接/图片/转义/行内 HTML 透传
    │  ├─ nl2br:段落内单换行转 <br>
    │  └─ 内置高亮器:正则 token 扫描,输出 Pygments 同款 CSS 类
    │
```

- [ ] **Step 6: 跨平台兼容小节增补**

在「跨平台兼容」小节末尾追加一行:

```markdown
- 零第三方依赖:`python -S`(跳过 site-packages)下可完整运行,不会出现 `No module named markdown`
```

- [ ] **Step 7: 重新生成 HTML 并全量验证**

Run: `python md2html.py "md2html工具说明.md"`
Expected: `[OK] Generated: ...`;检查输出包含「零第三方依赖」

Run: `grep -c "No module named markdown" "md2html工具说明.html"`
Expected: ≥ 1(文档已说明该问题不会再出现)

Run: `python -m unittest test_md2html -v` → 60/60 OK

Run: `python -S md2html.py "md2html工具说明.md"` → `[OK] Generated:`(零依赖回归)

- [ ] **Step 8: 浏览器结构检查**

打开 `md2html工具说明.html` 检查(子代理可做结构 grep 代理,视觉由用户确认):
- `grep -c 'class="highlight"'` ≥ 1 且 `grep -c '<span class="k"'` ≥ 1(高亮 span 存在)
- `grep -c '<table>'` ≥ 1(表格)
- `grep -c '<blockquote>'` ≥ 1(引用)
- `grep -c 'sec-num'` ≥ 1(章节编号)

- [ ] **Step 9: 提交**

```bash
git add md2html工具说明.md md2html工具说明.html
git commit -m "docs: 零依赖说明更新(移除 pip 安装指引,技术实现章节更新)"
```

---

## Self-Review 记录

- **Spec 覆盖:** 组件 1 块级解析 → Task 2;组件 2 高亮器 → Task 3;集成改动(import/convert/docstring)→ Task 4;测试 → Task 1(28 用例)与各任务验证;文档 → Task 5;`python -S` 零依赖验证 → Task 4 Step 4 与 Task 5 Step 7;launchers 零改动(spec 要求)✓
- **占位符扫描:** 所有步骤均为完整代码/命令,无 TBD/TODO
- **类型一致性:** `markdown_to_html(md_text) -> str` 在 Task 1 测试、Task 2 定义、Task 4 调用一致;`highlight_code(code, lang) -> str` 在 Task 2 stub、Task 3 实现、Task 1 测试一致;`_parse_list/_parse_table` 返回 `(html, next_i)` 两处调用一致;`_HL_SPECS` 键名(python/bash/yaml/json/sql/c/cpp/javascript/bat/html)与 `_HL_ALIASES` 引用一致;spec 要求代码块输出 `<div class="highlight"><pre><code class="language-lang">` — Task 2 实现与 Task 1 断言一致
