FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pre-install Aegra and core dependencies for speed
RUN pip install --no-cache-dir \
    aegra \
    langgraph-checkpoint-postgres \
    langchain-openai \
    pydantic \
    python-dotenv

COPY . .

# Aegra server command
ENTRYPOINT ["aegra", "serve", "--port", "8000", "--host", "0.0.0.0"]
