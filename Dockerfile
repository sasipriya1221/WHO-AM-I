FROM python:3.12-slim
WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend
WORKDIR /app/backend
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
