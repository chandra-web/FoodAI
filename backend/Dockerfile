FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all required modules
COPY backend /app/backend
COPY mcp_servers /app/mcp_servers
COPY skills /app/skills
COPY security /app/security
COPY database /app/database
COPY models /app/models
COPY agent /app/agent

ENV PYTHONPATH="/app:${PYTHONPATH}"

# Cloud Run expects the port to be configurable via the PORT environment variable
ENV PORT=8000
EXPOSE $PORT

# Start FastAPI server
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
