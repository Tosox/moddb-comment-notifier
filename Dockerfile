# Use official Python slim image
FROM python:3.12-slim

# Set workdir
WORKDIR /app

# Copy dependencies list and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src

# Set default command to run the notifier
CMD ["python", "-u", "-m", "src.main"]
