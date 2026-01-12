# Use official Playwright Python image which includes browsers
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY check_ordination.py .

# Run the script
CMD ["python3", "check_ordination.py"]
