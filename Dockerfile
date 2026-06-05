# ============================================================================
# Stage 1: Build React frontend
# ============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /build

COPY web/package.json web/package-lock.json ./
RUN npm ci --prefer-offline

COPY web/ ./
RUN npm run build

# ============================================================================
# Stage 2: Runtime image
# ============================================================================
FROM python:3.10-slim AS runtime

LABEL maintainer="CGCPT Team"
LABEL description="CGCPT Server - Crystal Glass-Ceramic Phase Transition analysis platform"

# System dependencies for numpy / pymatgen / scipy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libopenblas0 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY api_server.py .
COPY config.py .
COPY cgcpt_plugin.py .
COPY data_tools.py .
COPY logger.py .
COPY gunicorn.conf.py .
COPY MANIFEST.in .

# Copy database directory (CIF files, JSON indexes)
COPY database/ ./database/

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/dist ./web/dist

# Create directories for runtime data
RUN mkdir -p /app/uploads /app/models

# Environment defaults (override at runtime)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CGCPT_HOST=0.0.0.0 \
    CGCPT_PORT=5000 \
    CGCPT_DEBUG=false

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

CMD ["gunicorn", "api_server:app", "-c", "gunicorn.conf.py", "-b", "0.0.0.0:5000"]
