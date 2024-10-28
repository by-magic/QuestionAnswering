FROM python:3.9-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
# Copy the requirements file and install dependencies
COPY ./requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Add application files
ADD ./data /data
ADD ./preprocessing /preprocessing
COPY ./config.py .
COPY ./telegram_bot.py .

# Command to run your application
CMD [ "python3", "telegram_bot.py" ]