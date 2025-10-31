# ------------------------------
# Agent Builder 01 - Dockerfile
# ------------------------------

FROM python:3.12-slim

WORKDIR /app

# Kopiraj requirements i instaliraj (bolji cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Kopiraj ostatak
COPY . /app

# Render daje dinamički $PORT — ne hardcodamo 8000
ENV PYTHONUNBUFFERED=1

# Expose je informativan; Render svejedno koristi $PORT
EXPOSE 8000

# Start (sluša na $PORT koji Render postavi)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
