FROM python:3.12-slim

WORKDIR /app

# Install Node.js for building frontend
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app
COPY app ./app
COPY .env .

# Expose port (HF Spaces uses 7860 by default)
EXPOSE 7860

# Run uvicorn
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "7860"]