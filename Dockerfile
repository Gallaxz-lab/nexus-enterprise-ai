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
# Added --no-warn-script-location to clean out standard pip warnings completely
RUN pip install --no-cache-dir --user --no-warn-script-location -r requirements.txt

# ======================================================================================
# STAGE 2: PRODUCTION RUNTIME ENVIRONMENT
# ======================================================================================
FROM python:3.11-slim as runner

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user space context first
RUN useradd -u 8888 -m nexususer

# Transfer wheels directly into the non-privileged user's directory namespace
COPY --from=builder /root/.local /home/nexususer/.local
COPY . .

# Adjust file ownership parameters to give the app runner full clearance
RUN chown -R nexususer:nexususer /workspace /home/nexususer/.local

USER nexususer

# Update paths to evaluate from the non-root local directory context instead of root
ENV PATH=/home/nexususer/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
