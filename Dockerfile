FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.prod.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 7878

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MODEL_SIZE=large-v3
ENV BACKEND=faster-whisper
ENV LANGUAGE=en
ENV PATH="/usr/bin:${PATH}"

# Run the application
CMD ["python3", "simple.py"] 