# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cloud Classroom is a Django-based web application that acts as a proxy between DigitalOcean's infrastructure and students in educational settings. It solves the problem of requiring credit cards and managing resources for classroom cloud computing by providing teachers with controlled student access to cloud resources.

**Current Refactoring Status**: The project is being modernized from a Django REST Framework API to a full Django application with HTMX for interactivity, moving from Python 3.8 to 3.12+, and adopting modern tooling.

## Tech Stack
- Python 3.12+ (updated from 3.8.5)
- Django 5.0+ (upgrading from 3.1.12)
- HTMX + Alpine.js for frontend interactivity
- Tailwind CSS for styling
- PostgreSQL for production, SQLite for development
- aiohttp for async DigitalOcean API calls (replacing python-digitalocean)
- Temporal for workflow orchestration
- uv for package management (replacing pip)

## Development Commands

### Environment Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip sync

# Install development dependencies
uv pip install -e ".[dev]"

# Load environment variables
export $(grep -v '^#' env | xargs)

# Run migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Populate development data (Harry Potter themed)
uv run python manage.py shell < development_db_data.py
```

### Running the Application
```bash
# Development server
uv run python manage.py runserver 0.0.0.0:8000

# Production server
uv run gunicorn do_classroom.wsgi:application
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_droplets.py

# Run Django tests (legacy)
uv run python manage.py test
```

### Code Quality
```bash
# Format code with ruff
uv run ruff format .

# Lint code
uv run ruff check . --fix

# Type checking
uv run mypy .

# Run all pre-commit hooks
pre-commit run --all-files

# Install pre-commit hooks
pre-commit install
```

### Database Commands
```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

## Architecture

### Django Apps Structure
- **users**: Core user model with role-based access (Admin/Teacher, Student)
- **auth**: Authentication endpoints for login/logout
- **classes**: Classroom management with resource constraints (droplet limits, sizes, regions)
- **students**: Student management and registration
- **teachers**: Teacher management functionality
- **droplet**: DigitalOcean droplet lifecycle management with cloud-init integration
- **resources**: Available DO resources (sizes, regions, images)

### API Structure
- `/auth/` - Authentication (login, logout, token management)
- `/droplets/` - Droplet CRUD operations
- `/classes/` - Class management endpoints
- `/resources/` - DO resource listings
- `/users/` - User management
- `/` - Swagger API documentation
- `/schema/` - OpenAPI schema

### Key Features
1. **Multi-tenancy**: Each class has a unique prefix for DO resources
2. **Resource Constraints**: Teachers can limit droplet sizes, regions, and images per class
3. **Automated Provisioning**: Cloud-init scripts for droplet configuration
4. **SSH Key Management**: Automatic injection of teacher SSH keys into student droplets
5. **Password Generation**: Secure passwords for droplet access

### Environment Variables Required
```bash
# Django settings
DJANGO_SECRET_KEY=<secret_key>
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DEBUG=True  # Set to False in production
DEVELOPMENT_MODE=True  # Use SQLite when True, PostgreSQL when False

# PostgreSQL (when not in development mode)
DB_NAME=<database_name>
DB_USER=<database_user>
DB_PASSWORD=<database_password>
DB_HOST=<database_host>
DB_PORT=<database_port>

# DigitalOcean
DO_TOKEN=<digitalocean_api_token>
```

## Development Notes

1. **Authentication**: Uses DRF TokenAuthentication, BasicAuthentication, and SessionAuthentication
2. **API Documentation**: Available at root URL `/` using drf-spectacular with Swagger UI
3. **Database**: SQLite for development (DEVELOPMENT_MODE=True), PostgreSQL for production
4. **Static Files**: Swagger documentation in `/swagger-docs/`
5. **Test Structure**: Test files exist in each app but are currently empty stubs

## Common Development Tasks

### Adding New API Endpoints
1. Create views in the appropriate app's `views.py`
2. Add serializers in `serializers.py`
3. Update URLs in the app's `urls.py`
4. Include app URLs in main `do_classroom/urls.py`

### Working with DigitalOcean Integration
- DO API client is initialized in views using environment variable `DO_TOKEN`
- Droplet management includes create, list, delete, and action operations
- Cloud-init scripts are used for automated droplet configuration

### Database Schema Updates
1. Make changes to models in the appropriate app
2. Run `python manage.py makemigrations`
3. Review generated migration files
4. Apply with `python manage.py migrate`