import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from taskforge.store import Store, TaskError


class TaskForgeTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'tasks.db'
        self.store = Store(self.path)

    def test_filter_order_and_unicode(self):
        low = self.store.add('Написать отчёт', priority=1, tags=['Работа', ' работа '])
        high = self.store.add('Проверить ОТЧЁТ', priority=3, tags=['работа', 'срочно'])
        self.assertEqual([t['id'] for t in self.store.list(tag='РАБОТА', query='отчёт')], [high, low])
        self.assertEqual(self.store.list()[1]['tags'], ['работа'])

    def test_lifecycle_and_stats(self):
        task = self.store.add('Past', due='2024-01-01')
        today = date(2024, 1, 2)
        self.store.add('Today', due='2024-01-02')
        self.assertEqual([t['id'] for t in self.store.list(overdue=True, today=today)], [task])
        self.store.set_completed(task, True)
        self.assertEqual(self.store.stats(today), {'total': 2, 'open': 1, 'done': 1, 'overdue': 0})
        self.store.set_completed(task, False)
        self.assertEqual(self.store.stats(today)['overdue'], 1)
        self.store.delete(task)
        self.assertEqual(self.store.stats(today)['total'], 1)
        with self.assertRaises(TaskError):
            self.store.delete(task)

    def test_validation(self):
        for title, due, priority in [(' ', None, 2), ('Test', '2024-02-30', 2), ('Test', None, 4)]:
            with self.subTest(title=title, due=due, priority=priority), self.assertRaises(TaskError):
                self.store.add(title, due, priority)
        self.assertEqual(self.store.list(), [])

    def test_cli_persistence_and_export(self):
        def run(*args):
            return subprocess.run([sys.executable, '-m', 'taskforge', '--db', str(self.path), *args],
                                  capture_output=True, text=True, encoding='utf-8', env=self.utf8_env())

        self.assertEqual(run('add', 'Купить кофе', '--tag', 'дом').returncode, 0)
        self.assertIn('Купить кофе', run('list').stdout)
        output = self.path.with_name('export.json')
        self.assertEqual(run('export', '--output', str(output)).returncode, 0)
        data = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['tasks'][0]['tags'], ['дом'])
        self.assertEqual(run('export', '--output', str(output)).returncode, 1)
        self.assertEqual(run('done', '999').returncode, 1)

    @staticmethod
    def utf8_env():
        import os
        return dict(os.environ, PYTHONIOENCODING='utf-8')
