# Use Python 3.10 as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies including CA certificates and ffmpeg
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ca-certificates \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Specifically update yt-dlp to the latest version
RUN pip install --no-cache-dir --upgrade yt-dlp certifi

# Ensure Python uses the system CA certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV PYTHONHTTPSVERIFY=1

# Copy application code
COPY . .

# Set Python path to include the current directory
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "mainZ.py"]
