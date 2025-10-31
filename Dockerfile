# ------------------------------
# Agent Builder 01 - Dockerfile
# ------------------------------

FROM python:3.12-slim

WORKDIR /app

# 1️⃣  prvo requirements.txt (bolji cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 2️⃣  zatim ostatak koda
COPY . /app

# 3️⃣  postavi environment varijable
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# 4️⃣  ključna razlika — koristi "sh -c" da Render ispravno proširi $PORT
CMD sh -c "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
