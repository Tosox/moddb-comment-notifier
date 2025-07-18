# Use official Python slim image
FROM python:3.12-slim

# Set workdir
WORKDIR /app

# Copy dependencies list and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the python script
COPY moddb_comment_notifier.py .

# Set default command to run your notifier
CMD ["python", "-u", "moddb_comment_notifier.py"]
