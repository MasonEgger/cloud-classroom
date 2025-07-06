FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy source code
COPY . .

# Install the package in development mode
RUN uv sync --frozen

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "cloud_classroom.main:app", "--host", "0.0.0.0", "--port", "8000"]