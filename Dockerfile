# =============================================================================
# AgriSure Production Dockerfile
# Multi-stage optimized Python 3.9 container
# =============================================================================

FROM python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_HOME=/app

# Install system dependencies needed for psycopg2, pillow, and reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libfreetype6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create working directory and dedicated non-root user
WORKDIR $APP_HOME
RUN groupadd -r agrisure && useradd -r -g agrisure -d $APP_HOME agrisure

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create media and static directories and set correct ownership
RUN mkdir -p $APP_HOME/staticfiles $APP_HOME/media && \
    chown -R agrisure:agrisure $APP_HOME

# Switch to non-root user for security
USER agrisure

# Expose web service port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command launches WSGI server via Gunicorn
CMD ["gunicorn", "agrisure.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "60"]
