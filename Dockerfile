FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 7878

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MODEL_SIZE=large-v3
ENV BACKEND=mlx-whisper
ENV LANGUAGE=en

# Run the application
CMD ["python3", "simple.py"] 