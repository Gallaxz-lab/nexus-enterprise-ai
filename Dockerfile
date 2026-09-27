# ======================================================================================
# STAGE 1: COMPILATION BUILD ENVIRONMENT
# ======================================================================================
FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ======================================================================================
# STAGE 2: PRODUCTION RUNTIME ENVIRONMENT
# =================────────────────=====================================================
FROM python:3.11-slim as runner

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Transfer safely isolated wheel configurations from builder layer
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Create a non-privileged user space context to lock runtime execution privileges
RUN useradd -u 8888 nexususer && chown -R nexususer:nexususer /workspace
USER nexususer

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
