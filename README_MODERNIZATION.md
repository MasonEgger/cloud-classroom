# Cloud Classroom Modernization Guide

## Overview

This project is undergoing a major modernization effort to update from Django 3.1 to Django 5.0+, adopt modern Python tooling, and transition from a pure REST API to a full-stack Django application with HTMX.

## Modern Development Setup

### Prerequisites

- Python 3.12 or higher
- uv (modern Python package manager)

### Quick Start

1. **Install uv** (if not already installed):
```bash
# On macOS and Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. **Clone and setup the project**:
```bash
git clone https://github.com/MasonEgger/cloud-classroom.git
cd cloud-classroom

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"
```

3. **Setup environment variables**:
```bash
# Copy the example env file
cp env.example env

# Edit env file with your settings
# Required: DO_TOKEN (DigitalOcean API token)

# Load environment variables
export $(grep -v '^#' env | xargs)
```

4. **Initialize the database**:
```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

5. **Run the development server**:
```bash
uv run python manage.py runserver
```

Visit http://localhost:8000 to see the application.

## Development Workflow

### Code Quality

The project uses modern Python tooling for code quality:

- **Ruff**: All-in-one Python linter and formatter (replaces black, isort, flake8, pylint)
- **mypy**: Static type checking
- **pre-commit**: Git hooks for code quality

```bash
# Format code
uv run ruff format .

# Lint and auto-fix issues
uv run ruff check . --fix

# Type checking
uv run mypy .

# Install pre-commit hooks (one-time setup)
pre-commit install

# Run all pre-commit hooks manually
pre-commit run --all-files
```

### Testing

```bash
# Run all tests with pytest
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test
uv run pytest tests/test_droplets.py::test_create_droplet
```

## Architecture Changes

### Frontend (In Progress)
- Moving from REST API + separate frontend to Django templates + HTMX
- Tailwind CSS for styling
- Alpine.js for minimal JavaScript when needed
- Server-side rendering with dynamic updates via HTMX

### Backend (In Progress)
- Django 5.0+ with async view support
- Replacing `python-digitalocean` with `aiohttp` for async DO API calls
- Temporal for workflow orchestration (droplet provisioning, bulk operations)
- Modern authentication with django-allauth

### Key Improvements
1. **Type Safety**: Full type hints with Pydantic models
2. **Async Support**: Native async/await for external API calls
3. **Better Error Handling**: Structured logging with structlog
4. **Modern Tooling**: uv, ruff, pre-commit
5. **Simplified Frontend**: HTMX reduces JavaScript complexity

## Migration Status

- [x] Phase 1: Modern tooling setup (uv, ruff, Python 3.12+)
- [ ] Phase 2: Django 5.0 upgrade
- [ ] Phase 3: Frontend refactor to HTMX
- [ ] Phase 4: DigitalOcean API async refactor
- [ ] Phase 5: Temporal integration
- [ ] Phase 6: Enhanced features

## Contributing

1. Ensure pre-commit hooks are installed: `pre-commit install`
2. Use uv for all package management
3. Follow the established patterns in the codebase
4. Write tests for new functionality
5. Ensure all tests pass and code quality checks succeed

## Troubleshooting

### uv Issues
- Ensure you're using Python 3.12+: `python --version`
- Try clearing uv cache: `uv cache clean`
- Reinstall dependencies: `uv pip install -e ".[dev]" --force-reinstall`

### Import Errors
- Make sure virtual environment is activated
- Verify all dependencies installed: `uv pip list`

### Database Issues
- Reset database: `rm db.sqlite3 && uv run python manage.py migrate`
- Check migrations: `uv run python manage.py showmigrations`