FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 nemo && chown -R nemo:nemo /app
USER nemo

# Expose port (if needed for health checks)
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
