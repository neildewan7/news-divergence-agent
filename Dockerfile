FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching — only rebuilds if requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source after deps so code changes don't invalidate the pip layer
COPY . .

ENV PORT=8080

CMD ["python", "src/app.py"]
