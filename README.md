# Backend

[Wiki](wiki/index.md)

# Run

In order to run the backend:

1. Install **uv** on your system
2. cd into the backend repository, run `uv sync` - the project dependencies will be installed in a virtual environment
3. `uv python run -m src.main` or  `source .venv/bin/activate; uvicorn main:app --host 0.0.0.0 --reload` will run the server, it will be available at *localhost:8000*

## Run with Docker (backend + PostgreSQL)

Step-by-step local запуск через контейнеры:

1. Установить Docker Desktop.
2. Создать `.env` в корне `backend` (минимум):

	```bash
	DATABASE_URL=postgresql+asyncpg://postgres:password@postgres/backend_db
	SECRET_KEY=your-secret-key-here
	```

3. Запустить сервисы:

	```bash
	docker compose up -d postgres backend
	```

4. Проверить API: `http://localhost:8083/docs`.
5. Остановить:

	```bash
	docker compose down
	```

Опционально: `pgadmin` доступен на `http://localhost:28080` (логин/пароль в `docker-compose.yml`).

# Notifications

Система уведомлений строится на шаблонах и payload:

- `template_key` определяет тип уведомления.
- `payload` содержит данные для подстановки в шаблон.
- `title` и `body` формируются в сервисе через `.format(**payload)`.

Поддерживаемые типы (`NotificationType`):

- `project_invitation`
- `project_removal`
- `join_request`
- `join_request_approved`
- `join_request_rejected`
- `project_announcement`
- `system_alert`

Пример: шаблон `project_announcement` требует `payload` с `project_name` и `message`.

Шаблоны описаны в [src/notifications/templates.py](src/notifications/templates.py):

- `title` и `body` — строки с плейсхолдерами вида `{project_name}`.
- `required` — список полей, которые обязаны быть в `payload`.
- При отправке сервис подставляет данные через `.format(**payload)` и валидирует наличие `required`.

### Endpoints

- `GET /v1/notifications` — список уведомлений пользователя
- `POST /v1/users/{user_id}/notifications` — отправка пользователю
- `POST /v1/projects/{project_id}/notifications` — отправка участникам проекта
- `PATCH /v1/notifications/{notification_id}` — отметить прочитанным
- `PATCH /v1/notifications` — отметить все прочитанными
- `GET /v1/notifications/templates` — обязательные поля шаблонов
- `GET /v1/notifications/settings` — получить настройки уведомлений
- `PATCH /v1/notifications/settings` — обновить настройки уведомлений

# Development

## Code Quality Tools

This project uses **Ruff** for code linting, formatting, and import sorting. Ruff is configured in `pyproject.toml` and provides fast, comprehensive code quality checks.

### Installing Development Dependencies

```bash
# Install development dependencies including Ruff
uv sync --extra dev
```

### Using Ruff

#### Basic Commands

```bash
# Check code quality without making changes
uv run ruff check .

# Fix automatically fixable issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Check and format in one command
uv run ruff check . --fix && uv run ruff format .
```

#### Advanced Usage

```bash
# Check specific files or directories
uv run ruff check src/
uv run ruff check src/api/v1/endpoints/user.py

# Show detailed output
uv run ruff check . --output-format=full

# Only check for specific rule types
uv run ruff check . --select=E,W,F  # Only errors, warnings, and flakes
uv run ruff check . --ignore=E501   # Ignore specific rules

# Export configuration
uv run ruff config
```

### Pre-commit Hooks

The project includes pre-commit hooks that automatically run Ruff checks before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks on all files manually
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

### Configuration

Ruff configuration is located in `pyproject.toml` under `[tool.ruff]` section. Key settings:

- **Target Python version**: 3.12
- **Line length**: 120 characters
- **Excluded directories**: `.git`, `__pycache__`, `build`, `dist`, `.venv`, `.env`, migrations
- **Enabled rules**: Comprehensive set including style checks, bug detection, and modern Python features

### IDE Integration

Most modern IDEs support Ruff integration:

- **VS Code**: Install the "Ruff" extension
- **PyCharm**: Configure as external tool in Settings/Preferences
- **Vim/Neovim**: Use plugins like `ALE` or `null-ls`

### Continuous Integration

Ruff is configured to run in CI/CD pipelines. The same commands used locally will work in CI:

```bash
uv run ruff check .
uv run ruff format . --check
```

### Troubleshooting

#### Common Issues

1. **Import sorting conflicts**: Ruff uses isort-compatible sorting. Configure in `[tool.ruff.lint.isort]`
