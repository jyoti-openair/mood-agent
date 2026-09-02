# 1. Base Image: Lightweight Python 3.11 environment
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set working directory inside the container
WORKDIR /app

# 2. Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 4. Copy PDF Data Directory explicitly
COPY data/pdfs ./data/pdfs

# 5. Copy the rest of the Application Source Code
COPY . .

# 6. Expose Application Port
EXPOSE 8000

# 7. Startup Command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]