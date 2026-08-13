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

def slugify(title):
    """Generate an HTML anchor ID from a heading title."""
    slug = title.lower()
    slug = re.sub(r'[^\w\s\-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug


def extract_first_h1(md_text):
    """Return the text of the first h1 heading, or None if the document has none."""
    in_fence = False
    for line in md_text.split('\n'):
        s = line.strip()
        if s.startswith('```') or s.startswith('~~~'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r'^#\s+(.+)$', line)
        if m:
            return m.group(1).strip()
    return None


def build_heading_index(md_text):
    """Extract all headings from markdown, assign section numbers.
    Returns (flat_list, tree_for_toc) where each entry has:
      level, depth, title, slug, num, children[]
    """
    lines = md_text.split('\n')
    flat = []
    counters = [0, 0, 0]  # [h2, h3, h4]

    for line in lines:
        m = re.match(r'^(#{2,4})\s+(.+)$', line)
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        slug = slugify(title)
        depth = level - 2  # 0=h2, 1=h3, 2=h4

        counters[depth] += 1
        for d in range(depth + 1, 3):
            counters[d] = 0

        parts = [str(counters[d]) for d in range(depth + 1) if counters[d] > 0]
        num = '.'.join(parts)

        flat.append({'level': level, 'depth': depth, 'title': title,
                     'slug': slug, 'num': num, 'children': []})

    # Build tree for TOC
    toc_items = []
    stack = []
    for h in flat:
        while stack and stack[-1]['depth'] >= h['depth']:
            stack.pop()
        if stack:
            stack[-1]['children'].append(h)
        else:
            toc_items.append(h)
        stack.append(h)

    return flat, toc_items


def add_heading_ids(html_body, heading_index):
    """Inject id + section number into h2/h3/h4 tags."""
    # Build lookup: title_text -> num
    # We need to match HTML headings (after tag/entity processing) to markdown headings
    # Strategy: process headings in order; the nth h2/h3/h4 in HTML = nth in heading_index
    idx = [0]  # mutable counter

    def inject_id(m):
        tag = m.group(1)
        title_html = m.group(2)
        plain = re.sub(r'<[^>]+>', '', title_html).strip()
        plain = plain.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        plain = plain.replace('&#39;', "'").replace('&quot;', '"')
        slug = slugify(plain)

        # Find matching heading in index (by closest slug match)
        i = idx[0]
        num = ''
        # Try exact slug match first, then fuzzy
        for j in range(i, min(i + 5, len(heading_index))):
            if heading_index[j]['slug'] == slug:
                num = heading_index[j]['num']
                idx[0] = j + 1
                break
        if not num and i < len(heading_index):
            num = heading_index[i]['num']
            idx[0] = i + 1

        if num:
            return f'<{tag} id="{slug}"><span class="sec-num">{num}</span> {title_html}</{tag}>'
        return f'<{tag} id="{slug}">{title_html}</{tag}>'

    return re.sub(r'<(h[234])>(.+?)</\1>', inject_id, html_body, flags=re.DOTALL)


def render_toc_html(toc_items):
    """Render sidebar TOC with section numbers."""
    def render(items):
        if not items:
            return ''
        html = '<ul>\n'
        for item in items:
            has_children = len(item['children']) > 0
            cls = ' class="has-children"' if has_children else ''
            html += (f'  <li{cls}><a href="#{item["slug"]}">'
                     f'<span class="toc-num">{item["num"]}</span> {item["title"]}</a>')
            if has_children:
                html += '\n' + render(item['children'])
            html += '</li>\n'
        html += '</ul>\n'
        return html
    return render(toc_items)


def convert(input_path, output_path, title=None):
    input_path = Path(input_path)
    md_text = input_path.read_text(encoding='utf-8')

    if title is None:
        title = extract_first_h1(md_text) or input_path.stem
    title_html = html.escape(title)
    source_name = html.escape(input_path.name)
    footer_date = datetime.now().strftime('%Y-%m')

    # Build heading index with section numbers (shared by TOC and content)
    heading_index, toc_items = build_heading_index(md_text)
    toc_html = render_toc_html(toc_items)

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

    # Remove the TOC section from body (everything from "目录" h2 through the following hr)
    body_html = re.sub(
        r'<h2>目录</h2>.*?<hr ?/?>\s*',
        '',
        body_html,
        flags=re.DOTALL
    )

    # Inject id + section number into all h2/h3/h4 headings
    body_html = add_heading_ids(body_html, heading_index)

    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_html}</title>
<style>
/* ============================================================
   Design Tokens
   ============================================================ */
:root {{
    --sidebar-width: 300px;
    --sidebar-bg: #111318;
    --sidebar-text: #8b949e;
    --sidebar-active: #e6edf3;
    --sidebar-hover: #1a1d25;
    --sidebar-accent: #6cb6ff;
    --sidebar-border: #1e2128;

    --bg: #ffffff;
    --bg-secondary: #f8f9fb;
    --text: #1f2328;
    --text-secondary: #656d76;
    --border: #d0d7de;
    --border-light: #e8ecf1;
    --code-bg: #f6f8fa;
    --table-stripe: #f6f8fa;
    --link: #0969da;
    --heading: #0d1117;
    --inline-code: #bf1a2f;
    --inline-code-bg: #fff0f1;

    --font-mono: "Cascadia Code", "Fira Code", "JetBrains Mono", "SF Mono", "Consolas", "Liberation Mono", monospace;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", Helvetica, Arial, sans-serif;

    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --shadow-xs: 0 1px 1px rgba(0,0,0,0.03);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
}}

@media (prefers-color-scheme: dark) {{
    :root {{
        --bg: #0d1117;
        --bg-secondary: #111820;
        --text: #c9d1d9;
        --text-secondary: #8b949e;
        --border: #30363d;
        --border-light: #21262d;
        --code-bg: #161b22;
        --table-stripe: #0d1117;
        --link: #6cb6ff;
        --heading: #f0f6fc;
        --inline-code: #ff7b72;
        --inline-code-bg: #2d1114;
    }}
}}

/* ============================================================
   Reset & Base
   ============================================================ */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; font-size: 15px; }}
body {{
    font-family: var(--font-sans);
    background: var(--bg);
    color: var(--text);
    line-height: 1.72;
    display: flex;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}
a {{ color: var(--link); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ============================================================
   Sidebar — dark panel, always
   ============================================================ */
.sidebar {{
    position: fixed; top: 0; left: 0;
    width: var(--sidebar-width); height: 100vh;
    background: var(--sidebar-bg);
    color: var(--sidebar-text);
    overflow-y: auto; overflow-x: hidden;
    z-index: 100;
    display: flex; flex-direction: column;
    scrollbar-width: thin;
    scrollbar-color: #2a2e38 transparent;
    border-right: 1px solid var(--sidebar-border);
}}
.sidebar::-webkit-scrollbar {{ width: 4px; }}
.sidebar::-webkit-scrollbar-track {{ background: transparent; }}
.sidebar::-webkit-scrollbar-thumb {{ background: #2a2e38; border-radius: 2px; }}

.sidebar-header {{
    padding: 22px 20px 16px;
    border-bottom: 1px solid var(--sidebar-border);
    flex-shrink: 0;
}}
.sidebar-header h2 {{
    font-size: 1rem; font-weight: 700; color: #e6edf3;
    letter-spacing: -0.01em; margin: 0 0 2px;
}}
.sidebar-header .subtitle {{
    font-size: 0.66rem; color: #484f58;
    text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600;
}}

.sidebar-nav {{ padding: 6px 0; flex: 1; overflow-y: auto; }}
.sidebar-nav ul {{ list-style: none; padding: 0; margin: 0; }}
.sidebar-nav li {{ margin: 0; }}

.sidebar-nav a {{
    display: flex; align-items: baseline; gap: 5px;
    padding: 4px 20px;
    color: var(--sidebar-text);
    font-size: 0.8rem; text-decoration: none;
    border-left: 3px solid transparent;
    transition: background 0.12s, border-color 0.12s, color 0.12s;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.sidebar-nav a:hover {{
    background: var(--sidebar-hover);
    color: var(--sidebar-active);
    text-decoration: none;
}}

/* Section number badge in sidebar */
.toc-num {{
    display: inline-block; min-width: 22px;
    font-size: 0.66rem; font-weight: 600;
    color: var(--sidebar-accent); opacity: 0.65;
    text-align: right; flex-shrink: 0;
    font-family: var(--font-mono); letter-spacing: -0.03em;
}}
.sidebar-nav a.active .toc-num {{ opacity: 1; }}

/* h2-level links */
.sidebar-nav > ul > li > a {{
    font-weight: 600; font-size: 0.83rem; padding: 6px 20px; color: #c4cdd9;
}}
.sidebar-nav > ul > li > a .toc-num {{ font-size: 0.7rem; min-width: 16px; color: #6cb6ff; }}
/* h3-level links */
.sidebar-nav ul ul a {{ padding-left: 38px; font-size: 0.78rem; }}
.sidebar-nav ul ul a .toc-num {{ font-size: 0.64rem; min-width: 28px; color: #8b949e; }}
/* h4-level links */
.sidebar-nav ul ul ul a {{ padding-left: 56px; font-size: 0.75rem; color: #6e7681; }}
.sidebar-nav ul ul ul a .toc-num {{ font-size: 0.62rem; min-width: 34px; color: #484f58; }}

/* Active state */
.sidebar-nav a.active {{
    background: linear-gradient(90deg, rgba(108,182,255,0.14) 0%, rgba(108,182,255,0.01) 100%);
    border-left-color: var(--sidebar-accent); color: #e6edf3;
}}

.sidebar-footer {{
    padding: 10px 20px; border-top: 1px solid var(--sidebar-border);
    font-size: 0.66rem; color: #484f58; flex-shrink: 0;
}}

/* ============================================================
   Main Content — generous but bounded width for readability
   ============================================================ */
.main {{
    margin-left: var(--sidebar-width);
    flex: 1; min-width: 0;
    padding: 48px 56px 120px;
    max-width: 1240px;
}}

/* ============================================================
   Typography
   ============================================================ */
h1, h2, h3, h4 {{ color: var(--heading); font-weight: 600; line-height: 1.3; position: relative; }}

h1 {{
    font-size: 2rem; font-weight: 700; margin: 0 0 8px;
    padding-bottom: 16px; border-bottom: 2px solid var(--border);
    letter-spacing: -0.03em;
}}
h2 {{
    font-size: 1.45rem; margin: 56px 0 18px;
    padding-bottom: 12px; border-bottom: 1px solid var(--border-light);
    letter-spacing: -0.02em;
}}
h3 {{
    font-size: 1.18rem; margin: 40px 0 14px;
    padding-left: 16px; border-left: 3px solid var(--sidebar-accent);
}}
h4 {{ font-size: 1.04rem; margin: 30px 0 12px; }}

/* Section number in content headings */
.sec-num {{
    display: inline-block; margin-right: 10px;
    font-family: var(--font-mono); font-weight: 600;
    color: var(--sidebar-accent); opacity: 0.72;
    letter-spacing: -0.03em; user-select: none;
}}
h2 .sec-num {{ font-size: 0.78em; opacity: 0.8; }}
h3 .sec-num {{ font-size: 0.82em; }}
h4 .sec-num {{ font-size: 0.86em; }}

p {{ margin: 0 0 16px; }}
strong {{ font-weight: 600; color: var(--heading); }}

/* ============================================================
   Admonition / Callout boxes (via blockquote)
   ============================================================ */
blockquote {{
    margin: 22px 0; padding: 14px 20px;
    border-left: 4px solid;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    font-size: 0.9rem; line-height: 1.65;
    position: relative;
}}
blockquote::before {{
    content: '';
    position: absolute; left: 0; top: 0; bottom: 0;
    width: 4px; border-radius: 4px 0 0 4px;
}}
/* Default tip style */
blockquote {{
    background: #f0f7ff;
    border-color: #58a6ff;
    color: #1f6fb0;
}}
@media (prefers-color-scheme: dark) {{
    blockquote {{ background: #0d1f33; color: #79c0ff; }}
}}
/* Warning style: first strong contains "注意"/"重要"/"警告" */
blockquote:has(strong) {{
    background: #fff8e1;
    border-color: #d29922;
    color: #7a5d00;
}}
@media (prefers-color-scheme: dark) {{
    blockquote:has(strong) {{ background: #2d2200; color: #d29922; }}
}}
blockquote p {{ margin-bottom: 6px; }}
blockquote p:last-child {{ margin-bottom: 0; }}

hr {{
    border: none; border-top: 1px solid var(--border-light);
    margin: 40px 0;
}}

/* ============================================================
   Code — inline & blocks
   ============================================================ */
code {{
    font-family: var(--font-mono);
    font-size: 0.87em;
    background: var(--code-bg);
    padding: 2px 7px; border-radius: var(--radius-sm);
}}
pre {{
    margin: 20px 0; border-radius: var(--radius-md);
    overflow-x: auto;
    border: 1px solid var(--border);
    background: var(--code-bg);
    box-shadow: var(--shadow-xs);
    position: relative;
}}
pre code {{
    display: block; padding: 18px 22px;
    border: none; background: transparent;
    font-size: 0.82rem; line-height: 1.6; tab-size: 4;
}}
h1 code, h2 code, h3 code, h4 code {{
    font-size: 0.9em; background: transparent; border: none; padding: 0; color: inherit;
}}

/* Inline code in prose */
p code, li code, td code, th code {{
    background: var(--inline-code-bg);
    color: var(--inline-code);
    border: 1px solid rgba(191,26,47,0.12);
    font-size: 0.85em; padding: 1px 6px;
}}
@media (prefers-color-scheme: dark) {{
    p code, li code, td code, th code {{
        border-color: rgba(255,123,114,0.18);
    }}
}}

/* ============================================================
   Syntax Highlighting (Pygments)
   ============================================================ */
.highlight {{ background: transparent !important; }}
.highlight pre {{ margin: 0; border: none; background: transparent !important; box-shadow: none; }}

@media (prefers-color-scheme: light) {{
    .highlight .k, .highlight .kd {{ color: #cf222e; font-weight: 600; }}
    .highlight .kt {{ color: #cf222e; }}
    .highlight .n  {{ color: #1f2328; }}
    .highlight .s, .highlight .s1, .highlight .s2, .highlight .se {{ color: #0a3069; }}
    .highlight .c, .highlight .c1, .highlight .cm, .highlight .cp {{ color: #6e7781; font-style: italic; }}
    .highlight .p  {{ color: #1f2328; }}
    .highlight .m, .highlight .mi, .highlight .mf {{ color: #0550ae; }}
    .highlight .o  {{ color: #cf222e; }}
    .highlight .nf, .highlight .na {{ color: #8250df; }}
    .highlight .nb, .highlight .bp {{ color: #0550ae; }}
    .highlight .nc {{ color: #8250df; }}
    .highlight .nv {{ color: #953800; }}
    .highlight .cpf {{ color: #0a3069; }}
    .highlight .w  {{ color: #afb8c1; }}
    .highlight .gh {{ color: #0550ae; font-weight: 600; }}
}}

@media (prefers-color-scheme: dark) {{
    .highlight .k, .highlight .kd {{ color: #ff7b72; }}
    .highlight .kt {{ color: #ff7b72; }}
    .highlight .n  {{ color: #c9d1d9; }}
    .highlight .s, .highlight .s1, .highlight .s2, .highlight .se {{ color: #a5d6ff; }}
    .highlight .c, .highlight .c1, .highlight .cm, .highlight .cp {{ color: #8b949e; font-style: italic; }}
    .highlight .p  {{ color: #c9d1d9; }}
    .highlight .m, .highlight .mi, .highlight .mf {{ color: #79c0ff; }}
    .highlight .o  {{ color: #ff7b72; }}
    .highlight .nf, .highlight .na {{ color: #d2a8ff; }}
    .highlight .nb, .highlight .bp {{ color: #79c0ff; }}
    .highlight .nc {{ color: #d2a8ff; }}
    .highlight .nv {{ color: #ffa657; }}
    .highlight .cpf {{ color: #a5d6ff; }}
    .highlight .w  {{ color: #484f58; }}
    .highlight .gh {{ color: #79c0ff; font-weight: 600; }}
}}

/* ============================================================
   Tables — clean & spacious
   ============================================================ */
table {{
    width: 100%; border-collapse: separate; border-spacing: 0;
    margin: 22px 0; font-size: 0.88rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md); overflow: hidden;
}}
thead {{ background: var(--bg-secondary); }}
th {{
    font-weight: 600; text-align: left;
    padding: 12px 16px;
    border-bottom: 2px solid var(--border);
    font-size: 0.78rem; color: var(--text-secondary);
    text-transform: uppercase; letter-spacing: 0.05em;
}}
td {{
    padding: 11px 16px;
    border-bottom: 1px solid var(--border-light);
    vertical-align: top;
}}
tr:last-child td {{ border-bottom: none; }}
tr:nth-child(even) {{ background: var(--table-stripe); }}
td code {{ font-size: 0.81rem; }}

/* ============================================================
   Mobile — collapsible sidebar
   ============================================================ */
.sidebar-toggle {{
    display: none; position: fixed; top: 12px; left: 12px; z-index: 200;
    background: var(--sidebar-bg); color: #c4cdd9;
    border: 1px solid var(--sidebar-border); border-radius: var(--radius-md);
    width: 40px; height: 40px; font-size: 1.1rem; cursor: pointer;
    align-items: center; justify-content: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}}
.sidebar-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 99; }}

@media (max-width: 900px) {{
    .sidebar-toggle {{ display: flex; }}
    .sidebar {{
        transform: translateX(-100%);
        transition: transform 0.25s cubic-bezier(0.4,0,0.2,1);
        width: 290px;
    }}
    .sidebar.open {{ transform: translateX(0); box-shadow: 4px 0 28px rgba(0,0,0,0.35); }}
    .sidebar.open + .sidebar-overlay, .sidebar-overlay.active {{ display: block; }}
    .main {{ margin-left: 0; padding: 24px 18px 60px; max-width: none; }}
    h1 {{ font-size: 1.55rem; }}
    h2 {{ font-size: 1.22rem; }}
    h3 {{ font-size: 1.05rem; padding-left: 12px; }}
    table {{ font-size: 0.78rem; }}
    th, td {{ padding: 7px 10px; }}
    pre code {{ font-size: 0.76rem; padding: 14px 16px; }}
}}
@media (max-width: 500px) {{
    .main {{ padding: 18px 12px 40px; }}
    h1 {{ font-size: 1.35rem; }}
}}

/* ============================================================
   Print
   ============================================================ */
@media print {{
    .sidebar, .sidebar-toggle, .sidebar-overlay {{ display: none !important; }}
    .main {{ margin-left: 0; padding: 0; max-width: 100%; }}
    body {{ font-size: 10pt; color: #000; background: #fff; }}
    pre, code {{ background: #f6f8fa; border: 1px solid #d0d7de; }}
    a {{ color: #000; }}
    h2, h3 {{ page-break-after: avoid; }}
    table, pre {{ page-break-inside: avoid; }}
}}

/* ============================================================
   Animations
   ============================================================ */
@keyframes fadeSlideIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.main h2, .main h3, .main h4 {{ animation: fadeSlideIn 0.4s ease both; }}

/* Skip-link for keyboard users */
.skip-link {{
    position: absolute; top: -100px; left: 16px;
    background: var(--sidebar-accent); color: #fff;
    padding: 10px 18px; z-index: 999; border-radius: var(--radius-sm);
    font-size: 0.85rem; font-weight: 500;
}}
.skip-link:focus {{ top: 16px; outline: 2px solid var(--sidebar-accent); outline-offset: 2px; }}
</style>
</head>
<body>

<a href="#main-content" class="skip-link">Skip to content</a>

<!-- Sidebar Toggle (mobile) -->
<button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle navigation">
    &#9776;
</button>

<!-- Sidebar -->
<aside class="sidebar" id="sidebar">
    <div class="sidebar-header">
        <h2>{title_html}</h2>
        <div class="subtitle">{source_name}</div>
    </div>
    <nav class="sidebar-nav" id="sidebarNav">
{toc_html}
    </nav>
    <div class="sidebar-footer">
        Auto-generated from {source_name} &middot; {footer_date}
    </div>
</aside>
<div class="sidebar-overlay" id="sidebarOverlay"></div>

<!-- Main Content -->
<main class="main" id="main-content">
{body_html}
</main>

<script>
(function() {{
    // =========================================
    // Mobile sidebar toggle
    // =========================================
    var sidebar = document.getElementById('sidebar');
    var toggleBtn = document.getElementById('sidebarToggle');
    var overlay = document.getElementById('sidebarOverlay');

    function openSidebar() {{
        sidebar.classList.add('open');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }}

    function closeSidebar() {{
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }}

    toggleBtn.addEventListener('click', function() {{
        sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    }});

    overlay.addEventListener('click', closeSidebar);

    // =========================================
    // Active link highlighting on scroll
    // =========================================
    var navLinks = [].slice.call(document.querySelectorAll('.sidebar-nav a'));
    var headings = [].slice.call(document.querySelectorAll('.main h2, .main h3, .main h4'));

    if (navLinks.length && headings.length) {{
        // Build a map: heading id -> nav link element
        var linkMap = {{}};
        navLinks.forEach(function(a) {{
            var href = a.getAttribute('href');
            if (href && href.startsWith('#')) {{
                linkMap[href.substring(1)] = a;
            }}
        }});

        // Collect heading positions
        function getHeadingPositions() {{
            return headings.map(function(h) {{
                return {{ id: h.id, top: h.getBoundingClientRect().top + window.pageYOffset - 80 }};
            }});
        }}

        var headingPositions = getHeadingPositions();

        function updateActive() {{
            var scrollY = window.pageYOffset;
            var activeId = null;

            for (var i = headingPositions.length - 1; i >= 0; i--) {{
                if (scrollY >= headingPositions[i].top) {{
                    activeId = headingPositions[i].id;
                    break;
                }}
            }}

            // Clear all
            navLinks.forEach(function(a) {{ a.classList.remove('active'); }});

            // Set active
            if (activeId && linkMap[activeId]) {{
                linkMap[activeId].classList.add('active');

                // Ensure parent is visible (scroll into view in sidebar)
                var el = linkMap[activeId];
                var sidebarNav = document.getElementById('sidebarNav');
                var elRect = el.getBoundingClientRect();
                var navRect = sidebarNav.getBoundingClientRect();
                if (elRect.bottom > navRect.bottom || elRect.top < navRect.top) {{
                    el.scrollIntoView({{ block: 'center', behavior: 'smooth' }});
                }}
            }}
        }}

        window.addEventListener('scroll', updateActive, {{ passive: true }});

        // Recalculate on resize
        var resizeTimer;
        window.addEventListener('resize', function() {{
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {{
                headingPositions = getHeadingPositions();
                updateActive();
            }}, 200);
        }}, {{ passive: true }});

        // Initial state
        updateActive();
    }}

    // =========================================
    // Smooth scroll for sidebar links
    // =========================================
    document.getElementById('sidebarNav').addEventListener('click', function(e) {{
        var target = e.target;
        if (target.tagName === 'A' && target.getAttribute('href').startsWith('#')) {{
            e.preventDefault();
            var id = target.getAttribute('href').substring(1);
            var el = document.getElementById(id);
            if (el) {{
                el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                // Close sidebar on mobile after click
                if (window.innerWidth <= 900) {{
                    closeSidebar();
                }}
            }}
        }}
    }});

    // =========================================
    // Keyboard shortcut: Ctrl+\\ to toggle sidebar
    // =========================================
    document.addEventListener('keydown', function(e) {{
        if (e.ctrlKey && e.key === '\\\\') {{
            e.preventDefault();
            sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
        }}
    }});
}})();
</script>

</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html_template)
    print(f"[OK] Generated: {output_path}")
    print(f"     Size: {len(html_template):,} bytes")
    print(f"     TOC entries: {toc_html.count('<li')}")


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
        help='output HTML file path (default: same name as the input '
             'with .html extension; README.html in directory mode)')
    parser.add_argument(
        '--title', default=None,
        help='HTML title (default: the first h1 heading in the document, '
             'or the input filename)')
    return parser


def resolve_paths(args, cwd=None):
    """Resolve (input_path, output_path, title) from parsed args.
    Returns None (after printing an error) if the input does not exist
    or the output path is an existing directory.
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
    input_path = input_path.resolve()

    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        if args.input is None:
            print("用法: md2html.py [input.md | 目录] [-o out.html] [--title T]", file=sys.stderr)
        return None

    if args.output is not None:
        p = Path(args.output)
        output_path = p if p.is_absolute() else cwd / p
    elif dir_mode:
        output_path = input_path.parent / 'README.html'
    else:
        output_path = input_path.with_suffix('.html')
    output_path = output_path.resolve()

    if output_path.is_dir():
        print(f"ERROR: {output_path} is a directory", file=sys.stderr)
        return None

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
