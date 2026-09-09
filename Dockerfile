FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime-only OS packages; keep the image small and predictable.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies before copying the application to maximize Docker layer reuse.
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY bot ./bot
COPY scripts ./scripts
COPY README.md RELEASE.md pyproject.toml render.yaml .env.example ./

# Do not run the bot as root.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin alimj \
    && mkdir -p /app/data /app/logs \
    && chown -R alimj:alimj /app
USER alimj

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT', '8080'), timeout=4).read()" \
  || exit 1

CMD ["python", "-m", "bot.main"]
