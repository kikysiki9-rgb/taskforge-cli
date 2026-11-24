"""Persistence and domain operations for TaskForge."""

import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import date
from pathlib import Path


class TaskError(ValueError):
    """An invalid task operation."""


class Store:
    def __init__(self, path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due TEXT,
                    priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 3),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tags (
                    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    PRIMARY KEY(task_id, name)
                );
                CREATE INDEX IF NOT EXISTS tags_name_idx ON tags(name, task_id);
                CREATE INDEX IF NOT EXISTS tasks_status_due_idx ON tasks(completed_at, due);
            ''')

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys = ON')
            yield db

    def add(self, title, due=None, priority=2, tags=()):
        title = title.strip()
        if not title:
            raise TaskError('title must not be empty')
        if due is not None:
            try:
                due = date.fromisoformat(due).isoformat()
            except ValueError as exc:
                raise TaskError('due date must be a valid ISO date (YYYY-MM-DD)') from exc
        if priority not in (1, 2, 3):
            raise TaskError('priority must be 1, 2 or 3')
        tags = sorted({tag.strip().casefold() for tag in tags if tag.strip()})
        with self.connection() as db:
            task_id = db.execute(
                'INSERT INTO tasks(title, due, priority) VALUES (?, ?, ?)',
                (title, due, priority),
            ).lastrowid
            db.executemany('INSERT INTO tags(task_id, name) VALUES (?, ?)',
                           [(task_id, tag) for tag in tags])
        return task_id

    def set_completed(self, task_id, completed):
        with self.connection() as db:
            result = db.execute('''UPDATE tasks SET completed_at = CASE WHEN ?
                THEN COALESCE(completed_at, CURRENT_TIMESTAMP) ELSE NULL END WHERE id = ?''',
                (completed, task_id))
            if not result.rowcount:
                raise TaskError(f'task #{task_id} does not exist')

    def delete(self, task_id):
        with self.connection() as db:
            result = db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            if not result.rowcount:
                raise TaskError(f'task #{task_id} does not exist')

    def list(self, status='open', tag=None, query=None, overdue=False, today=None):
        conditions, params = [], []
        if status == 'open':
            conditions.append('t.completed_at IS NULL')
        elif status == 'done':
            conditions.append('t.completed_at IS NOT NULL')
        elif status != 'all':
            raise TaskError('invalid status')
        if tag is not None:
            conditions.append('EXISTS (SELECT 1 FROM tags WHERE task_id = t.id AND name = ?)')
            params.append(tag.strip().casefold())
        if query is not None:
            conditions.append('instr(CASEFOLD(t.title), ?) > 0')
            params.append(query.casefold())
        if overdue:
            conditions.extend(['t.completed_at IS NULL', 't.due < ?'])
            params.append((today or date.today()).isoformat())
        where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''
        with self.connection() as db:
            db.create_function('CASEFOLD', 1, str.casefold)
            rows = db.execute('''SELECT t.*, g.name AS tag FROM tasks t
                LEFT JOIN tags g ON g.task_id = t.id''' + where + '''
                ORDER BY t.priority DESC, t.due IS NULL, t.due, t.id, g.name''', params)
            tasks = {}
            for row in rows:
                task_id = row['id']
                if task_id not in tasks:
                    tasks[task_id] = {key: row[key] for key in row.keys() if key != 'tag'}
                    tasks[task_id]['tags'] = []
                if row['tag'] is not None:
                    tasks[task_id]['tags'].append(row['tag'])
        return list(tasks.values())

    def stats(self, today=None):
        with self.connection() as db:
            row = db.execute('''SELECT count(*) AS total,
                count(completed_at) AS done,
                count(CASE WHEN completed_at IS NULL AND due < ? THEN 1 END) AS overdue
                FROM tasks''', ((today or date.today()).isoformat(),)).fetchone()
        return dict(row) | {'open': row['total'] - row['done']}

    def export_json(self):
        return json.dumps({'version': 1, 'tasks': self.list(status='all')},
                          ensure_ascii=False, indent=2)
