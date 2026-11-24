# TaskForge CLI

Локальный менеджер задач для терминала. Работает без сервера и интернета, хранит данные в SQLite. Требуется Python 3.10 или новее; сторонних зависимостей для запуска нет.

## Установка

<!-- // filepath: pyproject.toml -->
```sh
git clone https://github.com/kikysiki9-rgb/taskforge-cli.git
cd taskforge-cli
python -m pip install .
```

Из корня репозитория можно запускать и без установки: `python -m taskforge --help`.

## Быстрый старт

<!-- // filepath: taskforge/__main__.py -->
```sh
taskforge add "Подготовить отчёт" --due 2030-05-30 --priority 3 --tag работа
taskforge list --tag работа
taskforge list --overdue
taskforge done 1
taskforge stats
taskforge export --output tasks.json
```

`list` по умолчанию показывает открытые задачи. `--status all` включает завершённые, `--query` ищет подстроку в названии без учёта регистра. Приоритет 3 — самый высокий. Команда `reopen ID` возвращает задачу в работу, `delete ID` удаляет её окончательно.

База по умолчанию: `~/.taskforge/tasks.db`. Чтобы выбрать другую, укажите `taskforge --db ./demo.db list` или задайте `TASKFORGE_DB`. Экспорт выдаёт JSON со всеми задачами и не перезаписывает существующие файлы.

## Тесты

`python -m unittest discover -s tests -v`
