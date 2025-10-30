# Start with the official Python slim image
FROM python:3.12-slim

# Set the working directory
WORKDIR /usr/src/app

# Ensure proper file permissions for the working directory
RUN chmod 777 /usr/src/app

# Install system dependencies for building C extensions (needed by some Python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    libsodium-dev \
    libssl-dev \
    git \
    procps \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Upgrade pip, setuptools, and wheel to the latest versions
RUN pip3 install --upgrade pip setuptools wheel

# Copy requirements file and install dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Make sure start.sh is executable
RUN chmod +x start.sh

# Use CMD to run your script
CMD ["bash", "start.sh"]
