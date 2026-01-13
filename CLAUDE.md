## Project Overview

sqlsaber is a Django + Svelte 5 full-stack application using Inertia.js for SPA-like navigation without building a separate API. It uses PostgreSQL for the database and Procrastinate for async job processing.

## Development Commands

### Running Development Servers

**With Docker (recommended for full stack):**
```bash
docker compose up           # Start all services (web, worker, vite, db)
docker compose watch        # Start with file sync enabled
```

**Without Docker (local development):**
```bash
# Terminal 1: Frontend (runs both Vite and Tailwind in watch mode)
npm run dev

# Terminal 2: Django server
uv run python manage.py runserver

# Terminal 3: Background worker (if needed)
uv run python manage.py procrastinate worker --concurrency=5
```

## Architecture

### Frontend-Backend Integration (Inertia.js)

- Django views use `inertia.render()` to return Svelte page components
- Pages live in `frontend/js/pages/` and are resolved by name (e.g., `render(request, "Index")` → `Index.svelte`)
- CSRF is configured automatically via axios defaults in `frontend/js/main.js`

### Frontend Structure

- **Pages**: `frontend/js/pages/` - Svelte components rendered by Inertia
- **Components**: `frontend/js/components/` - Reusable app-specific components
- **UI Library**: `frontend/js/lib/components/ui/` - shadcn-svelte components
- **Utilities**: `frontend/js/lib/utils.ts` - `cn()` helper for Tailwind class merging

Path aliases:
- `@` → `frontend/js`
- `$lib` → `frontend/js/lib`

### Backend Structure

- **Django Cotton templates**: `templates/cotton/` - Server-rendered components for allauth views
- **Base template**: `templates/base.html` - Inertia root template with Vite asset loading

### Background Jobs

Uses Procrastinate for PostgreSQL-backed async task queue:
```python
from procrastinate.contrib.django import app

@app.task
def my_task(arg):
    ...
```

### Key Configuration

- Vite dev server runs on port 5173, Django on 8000
- `DJANGO_VITE_DEV_SERVER_HOST` and `DJANGO_VITE_DEV_SERVER_PORT` configure HMR
- Tailwind CSS 4 with `@tailwindcss/vite` plugin
- shadcn-svelte configured in `components.json`