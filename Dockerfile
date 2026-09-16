FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime-only OS packages; keep the image small and predictable.
ARG NODE_VERSION=22.19.0
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg curl git build-essential python3 pkg-config libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev \
    && curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /opt \
    && ln -s "/opt/node-v${NODE_VERSION}-linux-x64/bin/node" /usr/local/bin/node \
    && ln -s "/opt/node-v${NODE_VERSION}-linux-x64/bin/npm" /usr/local/bin/npm \
    && ln -s "/opt/node-v${NODE_VERSION}-linux-x64/bin/npx" /usr/local/bin/npx \
    && rm -f /tmp/node.tar.xz \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies before copying the application to maximize Docker layer reuse.
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt \
    && python -m pip install --no-cache-dir bgutil-ytdlp-pot-provider==2.0.0 yt-dlp-ejs==0.8.0

# Build the local BgUtils PO-token generator used by yt-dlp for YouTube mweb.
# The Python plugin and generator are deliberately pinned to the same release.
RUN git clone --depth 1 --branch 2.0.0 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil \
    && cd /opt/bgutil/server \
    && npm ci \
    && npx tsc \
    && test -f /opt/bgutil/server/build/generate_once.js

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
