# Use official Python 3.10 slim image
FROM python:3.10-slim

# Install FFmpeg and required system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the API and Dashboard ports
EXPOSE 5001

# Command to run the music dashboard
CMD ["python", "music_dashboard.py"]
