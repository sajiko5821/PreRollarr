FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY fallback_config.yaml .

# Create volume directories
RUN mkdir -p /config /preroll

# Ensure unbuffered output
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "-u", "main.py"]
