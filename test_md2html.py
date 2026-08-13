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

    def test_ignores_h1_inside_fenced_code(self):
        md = '```python\n# not a heading\n```\n# Real Title'
        self.assertEqual(md2html.extract_first_h1(md), 'Real Title')

    def test_tilde_fence_ignored(self):
        md = '~~~\n# not a heading\n~~~\n# Real Title'
        self.assertEqual(md2html.extract_first_h1(md), 'Real Title')

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

    def test_output_is_directory_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / 'guide.md').write_text('# T', encoding='utf-8')
            sub = cwd / 'outdir'
            sub.mkdir()
            self.assertIsNone(md2html.resolve_paths(
                self._args(input='guide.md', output='outdir'), cwd=cwd))

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
