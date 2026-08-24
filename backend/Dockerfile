FROM python:3.11-slim

WORKDIR /app

# ── Dependencies ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Backend source ────────────────────────────────────────────
COPY backend/ .

# ── Runtime ───────────────────────────────────────────────────
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]