# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cloud Classroom is a Django-based web application that acts as a proxy between DigitalOcean's infrastructure and students in educational settings. It solves the problem of requiring credit cards and managing resources for classroom cloud computing by providing teachers with controlled student access to cloud resources.

**Current Refactoring Status**: The project is being modernized from a Django REST Framework API to a full Django application with HTMX for interactivity, moving from Python 3.8 to 3.12+, and adopting modern tooling.

## Tech Stack
- Python 3.12+ (updated from 3.8.5)
- Django 5.0+ (upgraded from 3.1.12) 
- HTMX + Alpine.js for frontend interactivity
- Tailwind CSS for styling (via django-tailwind)
- PostgreSQL for production, SQLite for development
- aiohttp for async DigitalOcean API calls (modern async client in `services/digitalocean.py`)
- Pydantic for data validation and modeling
- Structlog for structured logging
- uv for package management (replaces pip)

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

# Load environment variables (optional - .env file is loaded automatically)
export $(grep -v '^#' env | xargs)
# OR create a .env file in the project root (recommended)

# Run migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Populate development data (Pokemon themed)
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
- **authentication**: Authentication views and forms for login/logout
- **classes**: Classroom management with resource constraints (droplet limits, sizes, regions)
- **students**: Student management and registration
- **teachers**: Teacher management functionality
- **droplet**: DigitalOcean droplet lifecycle management with cloud-init integration
- **resources**: Available DO resources (sizes, regions, images)
- **classroom**: Main classroom management app with HTMX-powered views
- **services**: Async service layer (`digitalocean.py`, `classroom.py`)
- **theme**: Tailwind CSS theme configuration

### URL Structure
- `/accounts/` - Django-allauth authentication (login, logout, signup)
- `/auth/` - Custom authentication views
- `/classroom/` - Main classroom management interface (HTMX-powered)
- `/admin/` - Django admin interface
- `/` - Home page
- **Note**: Some legacy API endpoints are commented out during modernization (droplets, classes, resources, users)

### Key Features
1. **Multi-tenancy**: Each class has a unique prefix for DO resources
2. **Resource Constraints**: Teachers can limit droplet sizes, regions, and images per class
3. **Automated Provisioning**: Cloud-init scripts for droplet configuration
4. **SSH Key Management**: Automatic injection of teacher SSH keys into student droplets
5. **Password Generation**: Secure passwords for droplet access
6. **Async Operations**: Modern async service layer for DigitalOcean API calls
7. **HTMX Interface**: Dynamic UI without complex JavaScript
8. **Structured Logging**: Comprehensive logging with structlog

### Environment Variables

The application automatically loads environment variables from a `.env` file in the project root. Environment variables set in the shell take precedence over `.env` file values.

Create a `.env` file in the project root with the following variables:

```bash
# Django settings
DJANGO_SECRET_KEY=<secret_key>
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DEBUG=True  # Set to False in production
DEVELOPMENT_MODE=True  # Use SQLite when True, PostgreSQL when False

# Workshop Mode Settings
SIMPLE_AUTH_MODE=True  # Enable workshop code registration (default: True)
MULTI_CLASS_MODE=False  # Enable multi-class management (default: False)

# PostgreSQL (when not in development mode)
DB_NAME=<database_name>
DB_USER=<database_user>
DB_PASSWORD=<database_password>
DB_HOST=<database_host>
DB_PORT=<database_port>

# DigitalOcean
DO_TOKEN=<digitalocean_api_token>
```

**Environment Variable Precedence:**
1. Shell environment variables (highest priority)
2. `.env` file values
3. Default values defined in settings.py (lowest priority)

## Development Notes

1. **Authentication**: Uses django-allauth for modern authentication with session support
2. **Frontend**: HTMX + Tailwind CSS with server-side rendering
3. **Database**: SQLite for development (DEVELOPMENT_MODE=True), PostgreSQL for production
4. **Async Services**: Modern async DigitalOcean client in `services/digitalocean.py`
5. **Service Layer**: `ClassroomService` in `services/classroom.py` orchestrates droplet operations
6. **Test Structure**: Pytest-based testing with async support
7. **Development Data**: Pokemon-themed sample data in `development_db_data.py`

## Common Development Tasks

### Adding New Views/Pages
1. Create HTMX-powered views in the appropriate app's `views.py`
2. Add templates in `templates/` directory
3. Update URLs in the app's `urls.py`
4. Include app URLs in main `do_classroom/urls.py`

### Working with DigitalOcean Integration
- Use the async `DigitalOceanClient` in `services/digitalocean.py`
- High-level operations available in `ClassroomService` in `services/classroom.py`
- Example: `async with ClassroomService() as service: await service.create_droplet_for_student(class_obj, student)`
- All droplet operations are async and include proper error handling

### Database Schema Updates
1. Make changes to models in the appropriate app
2. Run `uv run python manage.py makemigrations`
3. Review generated migration files
4. Apply with `uv run python manage.py migrate`

### Working with Async Views
- Django 5.0 supports async views natively
- Use `asgiref.sync.sync_to_async` to call sync Django ORM operations from async code
- Service layer handles async DigitalOcean operations properly

## Workshop Mode Configuration

The system supports two independent settings for flexible deployment scenarios:

### SIMPLE_AUTH_MODE (default: True)
Controls authentication method:
- **True**: Workshop code registration - users enter a code provided by instructor
- **False**: Email-based registration with verification

### MULTI_CLASS_MODE (default: False)  
Controls class management complexity:
- **False**: Single default class - all users join one class automatically
- **True**: Multi-class system - teachers can create/manage individual classes

### Four Deployment Modes

1. **Simple Workshop** (`SIMPLE_AUTH_MODE=True`, `MULTI_CLASS_MODE=False`)
   - Workshop codes for registration
   - Single default class for all participants
   - Perfect for single-day workshops

2. **Multi-Instructor Workshop** (`SIMPLE_AUTH_MODE=True`, `MULTI_CLASS_MODE=True`)
   - Workshop codes for registration
   - Multiple classes with different instructors
   - Each instructor manages their own participants

3. **Simple School** (`SIMPLE_AUTH_MODE=False`, `MULTI_CLASS_MODE=False`)
   - Email verification registration
   - Single default class

4. **Full Production** (`SIMPLE_AUTH_MODE=False`, `MULTI_CLASS_MODE=True`)
   - Email verification registration
   - Full class management system

### Workshop Registration Flow

**For Students:**
1. Visit `/auth/workshop/register/` or `/register/` (redirects in workshop mode)
2. Enter workshop code + basic info (name, preferred username)
3. Account created in "pending approval" state
4. Can't login until instructor approves

**For Instructors:**
1. Create workshop code in Django admin (`/admin/authentication/workshopcode/`)
2. Share code with participants
3. Review pending registrations in user admin (`/admin/users/user/`)
4. Bulk approve legitimate participants
5. Students can then login and access resources

### Workshop Code Management

Workshop codes include:
- Unique 8-character alphanumeric code (auto-generated)
- Workshop name and description
- Optional registration limits and expiration
- Link to specific class (when `MULTI_CLASS_MODE=True`)

Admin features:
- Bulk approval/rejection of workshop users
- Workshop statistics and registration tracking
- Automatic code generation and management