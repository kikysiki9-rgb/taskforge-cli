"""Command-line entry point."""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

from .store import Store, TaskError


def build_parser():
    parser = argparse.ArgumentParser(prog='taskforge', description='Offline task manager')
    parser.add_argument('--db', default=os.environ.get('TASKFORGE_DB', '~/.taskforge/tasks.db'),
                        help='SQLite database path')
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add', help='create a task')
    add.add_argument('title')
    add.add_argument('--due', metavar='YYYY-MM-DD')
    add.add_argument('--priority', type=int, choices=(1, 2, 3), default=2)
    add.add_argument('--tag', action='append', default=[])
    ls = commands.add_parser('list', help='show and filter tasks')
    ls.add_argument('--status', choices=('open', 'done', 'all'), default='open')
    ls.add_argument('--tag')
    ls.add_argument('--query')
    ls.add_argument('--overdue', action='store_true')
    for name, help_text in [('done', 'complete a task'), ('reopen', 'reopen a task'),
                            ('delete', 'permanently delete a task')]:
        commands.add_parser(name, help=help_text).add_argument('id', type=int)
    commands.add_parser('stats', help='show task counts')
    export = commands.add_parser('export', help='export all tasks as JSON')
    export.add_argument('--output', type=Path, help='write to a new file instead of stdout')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        store = Store(args.db)
        if args.command == 'add':
            print(f'Added task #{store.add(args.title, args.due, args.priority, args.tag)}')
        elif args.command == 'list':
            tasks = store.list(args.status, args.tag, args.query, args.overdue)
            if not tasks:
                print('No matching tasks.')
            for task in tasks:
                status = 'done' if task['completed_at'] else 'open'
                due = task['due'] or '-'
                tags = ', '.join(task['tags']) or '-'
                print(f"#{task['id']} [{status}] P{task['priority']} {task['title']} | due: {due} | tags: {tags}")
        elif args.command in ('done', 'reopen'):
            store.set_completed(args.id, args.command == 'done')
            print(f'Updated task #{args.id}')
        elif args.command == 'delete':
            store.delete(args.id)
            print(f'Deleted task #{args.id}')
        elif args.command == 'stats':
            stats = store.stats()
            for key in ('total', 'open', 'done', 'overdue'):
                print(f'{key}: {stats[key]}')
        elif args.command == 'export':
            payload = store.export_json() + '\n'
            if args.output is None:
                print(payload, end='')
            else:
                with args.output.open('x', encoding='utf-8') as output:
                    output.write(payload)
    except (TaskError, OSError, sqlite3.Error) as exc:
        print(f'taskforge: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
