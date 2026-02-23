# Use official Python lightweight image
FROM python:3.10-slim

# Install system dependencies (FFmpeg is critical)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p temp assets/music uploads

# Environment variables will be handled by Docker Compose or .env file

# Expose port for the dashboard
EXPOSE 5000

# We use a start script or docker-compose to run multiple processes
CMD ["python", "bot.py"]
