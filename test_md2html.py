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


class TestRecursive(unittest.TestCase):
    def _tree(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / 'a.md').write_text('# A', encoding='utf-8')
        (root / 'b.md').write_text('# B', encoding='utf-8')
        (root / 'sub').mkdir()
        (root / 'sub' / 'c.md').write_text('# C', encoding='utf-8')
        (root / '.hidden').mkdir()
        (root / '.hidden' / 'd.md').write_text('# D', encoding='utf-8')
        (root / 'note.txt').write_text('not markdown', encoding='utf-8')
        return tmp

    def test_recursive_converts_nested_md(self):
        with self._tree() as tmp:
            root = Path(tmp)
            self.assertEqual(md2html.main(['-r', str(root)]), 0)
            self.assertTrue((root / 'a.html').exists())
            self.assertTrue((root / 'b.html').exists())
            self.assertTrue((root / 'sub' / 'c.html').exists())
            self.assertFalse((root / 'note.txt.html').exists())

    def test_recursive_skips_hidden_dirs(self):
        with self._tree() as tmp:
            root = Path(tmp)
            md2html.main(['-r', str(root)])
            self.assertFalse((root / '.hidden' / 'd.html').exists())

    def test_recursive_with_file_input_errors(self):
        with self._tree() as tmp:
            root = Path(tmp)
            self.assertEqual(md2html.main(['-r', str(root / 'a.md')]), 1)

    def test_recursive_with_output_errors(self):
        with self._tree() as tmp:
            root = Path(tmp)
            self.assertEqual(md2html.main(['-r', '-o', 'x.html', str(root)]), 1)

    def test_recursive_with_title_errors(self):
        with self._tree() as tmp:
            root = Path(tmp)
            self.assertEqual(md2html.main(['-r', '--title', 'T', str(root)]), 1)

    def test_recursive_empty_dir_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(md2html.main(['-r', tmp]), 1)


class TestBatch(unittest.TestCase):
    def _chdir_tmp(self):
        tmp = tempfile.TemporaryDirectory()
        old = os.getcwd()
        os.chdir(tmp.name)
        return tmp, old

    def test_no_args_batches_cwd_top_level_only(self):
        tmp, old = self._chdir_tmp()
        try:
            Path('a.md').write_text('# A', encoding='utf-8')
            Path('b.md').write_text('# B', encoding='utf-8')
            Path('sub').mkdir()
            Path('sub', 'c.md').write_text('# C', encoding='utf-8')
            self.assertEqual(md2html.main([]), 0)
            self.assertTrue(Path('a.html').exists())
            self.assertTrue(Path('b.html').exists())
            self.assertFalse(Path('sub', 'c.html').exists())
        finally:
            os.chdir(old)
            tmp.cleanup()

    def test_no_args_skips_hidden_files(self):
        tmp, old = self._chdir_tmp()
        try:
            Path('a.md').write_text('# A', encoding='utf-8')
            Path('.hidden.md').write_text('# H', encoding='utf-8')
            md2html.main([])
            self.assertFalse(Path('.hidden.html').exists())
        finally:
            os.chdir(old)
            tmp.cleanup()

    def test_no_args_empty_dir_errors(self):
        tmp, old = self._chdir_tmp()
        try:
            self.assertEqual(md2html.main([]), 1)
        finally:
            os.chdir(old)
            tmp.cleanup()

    def test_no_args_with_output_errors(self):
        tmp, old = self._chdir_tmp()
        try:
            Path('a.md').write_text('# A', encoding='utf-8')
            self.assertEqual(md2html.main(['-o', 'x.html']), 1)
        finally:
            os.chdir(old)
            tmp.cleanup()

    def test_no_args_with_title_errors(self):
        tmp, old = self._chdir_tmp()
        try:
            Path('a.md').write_text('# A', encoding='utf-8')
            self.assertEqual(md2html.main(['--title', 'T']), 1)
        finally:
            os.chdir(old)
            tmp.cleanup()

    def test_no_args_recursive_includes_subdirs(self):
        tmp, old = self._chdir_tmp()
        try:
            Path('sub').mkdir()
            Path('sub', 'c.md').write_text('# C', encoding='utf-8')
            self.assertEqual(md2html.main(['-r']), 0)
            self.assertTrue(Path('sub', 'c.html').exists())
        finally:
            os.chdir(old)
            tmp.cleanup()


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
