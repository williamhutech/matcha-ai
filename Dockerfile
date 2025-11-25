FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.0

# Configure Poetry: no virtual env (we're in a container)
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN poetry install --no-root --only main

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
