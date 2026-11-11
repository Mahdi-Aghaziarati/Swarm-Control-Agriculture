import csv
import io
import json
import unittest
from pathlib import Path

from engine import Settings, analyze, load_image
from exports import csv_bytes

ROOT = Path(__file__).resolve().parents[1]


class ExportTests(unittest.TestCase):
    def test_csv_contains_all_markers_and_corners(self):
        image = load_image((ROOT / 'samples' / 'demo.webp').read_bytes())
        report = analyze(image, Settings(dictionary='DICT_4X4_250', enhanced=False))
        data = csv_bytes(report)
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        rows = list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        self.assertEqual(len(rows), 45)
        self.assertEqual(sorted(int(row['id']) for row in rows), list(range(100, 145)))
        self.assertEqual(len(json.loads(rows[0]['corners_px'])), 4)
        self.assertIsNone(json.loads(rows[0]['pose']))

    def test_empty_csv_keeps_header(self):
        data = csv_bytes({'markers': []}).decode('utf-8-sig')
        self.assertIn('corners_px', data)
        self.assertEqual(list(csv.DictReader(io.StringIO(data))), [])

    def test_source_and_ui_are_english(self):
        for name in ('app.py', 'engine.py', 'exports.py', 'README.md'):
            content = (ROOT / name).read_text(encoding='utf-8')
            self.assertFalse(any('\u0600' <= c <= '\u06ff' for c in content), name)


class DesktopSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
        except ImportError as exc:
            raise unittest.SkipTest(f'Tk runtime is unavailable: {exc}')
        try:
            root = tk.Tk()
            root.destroy()
        except tk.TclError as exc:
            raise unittest.SkipTest(f'Graphical display is unavailable: {exc}')
        from app import Studio
        cls.Studio = Studio

    def setUp(self):
        self.app = self.Studio()
        self.app.update()

    def tearDown(self):
        self.app._close()

    def test_demo_report_view_and_filter(self):
        self.app.demo()
        self.app.report = analyze(self.app.image, Settings(dictionary='DICT_4X4_250', enhanced=False))
        self.app.show_report()
        self.app.update()
        self.assertEqual(len(self.app.tree.get_children()), 45)
        self.assertIsNotNone(self.app.photo)
        self.app.filter_ids.set('100,101')
        self.app.refresh_image()
        self.assertEqual(self.app.selected_ids(), {100, 101})
        self.app.change_zoom(1.25)
        self.app.fit()
        self.app.tree.selection_set(self.app.tree.get_children()[0])
        self.app.marker_details()
        self.assertIn('corners_px', self.app.detail.get('1.0', 'end'))
        self.app.sort_table('id')
        first = self.app.tree.get_children()[0]
        self.assertEqual(int(self.app.tree.set(first, 'id')), 100)


if __name__ == '__main__':
    unittest.main()
