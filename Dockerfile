# Use lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Render injects PORT env var automatically)
EXPOSE 8080

# Use Gunicorn as production WSGI server
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120"]