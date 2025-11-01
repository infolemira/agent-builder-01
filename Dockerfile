# ------------------------------
# Agent Builder 01 - Dockerfile
# ------------------------------
FROM python:3.12-slim

# Radni direktorij unutar kontejnera
WORKDIR /app

# Instalacijske datoteke najprije (bolji cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Kopiraj ostatak izvornog koda
COPY . /app

# Osiguraj da je /app na PYTHONPATH-u (radi importa 'app')
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Port koji Render prosljeđuje
EXPOSE 8000

# Pokreni uvicorn; PORT dolazi iz Render env varijable
CMD ["/bin/sh","-lc","python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
