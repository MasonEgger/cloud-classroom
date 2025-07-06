# Cloud Classroom

Educational cloud resource management platform that eliminates barriers to hands-on cloud computing education.

## Overview

Cloud Classroom acts as an intelligent intermediary between educators and cloud infrastructure, providing students with supervised access to real cloud resources while maintaining institutional control over costs and resources.

## Features

- **Zero Student Financial Commitment**: Students get hands-on cloud experience without needing personal payment methods
- **Institutional Cost Control**: Educators set spending limits and resource constraints before any resources are provisioned
- **Automated Resource Management**: The system handles provisioning, monitoring, and cleanup of cloud resources
- **Real-World Experience**: Students work with actual cloud platforms, not simulations
- **Two Operation Modes**:
  - **Workshop Mode**: Simple access codes for short-term workshops (1-3 days)
  - **Academic Mode**: Full enrollment management for semester-long courses

## Quick Start

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cloud-classroom
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations**:
   ```bash
   uv run alembic upgrade head
   ```

5. **Start the development server**:
   ```bash
   uv run uvicorn cloud_classroom.main:app --reload
   ```

The application will be available at `http://localhost:8000`.

### Using Docker Compose

```bash
docker-compose up -d
```

## Architecture

- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Cloud Provider**: DigitalOcean (with modular design for multi-cloud support)
- **Provisioning**: Ansible playbooks via cloud-init

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Run with verbose output
uv run pytest -v
```

### Code Quality

```bash
# Linting and formatting
uv run ruff check
uv run ruff format

# Type checking
uv run mypy src/
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: JWT signing key (change in production!)
- `DIGITALOCEAN_TOKEN`: DigitalOcean API token
- `DEBUG`: Enable debug mode for development

## Deployment

### Docker Compose (Recommended)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Bare Metal

Use the provided Ansible playbooks in the `deploy/` directory.

## Contributing

1. Follow TDD principles - write tests first
2. Ensure all tests pass: `uv run pytest`
3. Check code quality: `uv run ruff check && uv run mypy src/`
4. Update documentation as needed

## License

[Add your license here]

## Support

For support and bug reports, please open an issue in the GitHub repository.