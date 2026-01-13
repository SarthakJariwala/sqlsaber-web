# sqlsaber - Agent Instructions

## Commands
```bash
# Development
docker compose up                          # Full stack with Docker
npm run dev                                # Frontend (Vite + Tailwind watch)
uv run python manage.py runserver          # Django server
uv run python manage.py migrate            # Run migrations
uv run python manage.py test               # Run all Django tests
uv run python manage.py test app.tests.TestClass.test_method  # Single test
```

## Architecture
- **Stack**: Django 5 + Svelte 5 + Inertia.js + PostgreSQL + Procrastinate (jobs)
- **Frontend**: `frontend/js/pages/` (Inertia pages), `frontend/js/components/`, `frontend/js/lib/components/ui/` (shadcn-svelte)
- **Backend**: `sqlsaber_web/` (Django project), `templates/cotton/` (server-rendered components)
- **Path aliases**: `@` → `frontend/js`, `$lib` → `frontend/js/lib`

## Code Style
- **Python**: Use `uv run` for all Python commands; follow Django conventions; use `ruff` for linting
- **Frontend**: Svelte 5 with TypeScript; use `cn()` from `$lib/utils` for Tailwind class merging
- **Inertia views**: Use `inertia.render(request, "PageName", props)` in Django views
- **Jobs**: Define with `@app.task` decorator from `procrastinate.contrib.django`
- **Imports**: Group stdlib, third-party, local; use absolute imports in Python
