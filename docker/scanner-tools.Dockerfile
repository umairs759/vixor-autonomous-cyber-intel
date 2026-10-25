# VIXOR — Scanner-tools container (subfinder, httpx, nmap, nuclei)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install OS dependencies for scanner binaries
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        wget \
        unzip \
        nmap \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install ProjectDiscovery tools (subfinder, httpx, nuclei)
RUN GO_VERSION=1.22.3 && \
    wget -q https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz -O /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz
ENV PATH=/usr/local/go/bin:$PATH

RUN go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && \
    cp /root/go/bin/subfinder /usr/local/bin/ && \
    cp /root/go/bin/httpx /usr/local/bin/ && \
    cp /root/go/bin/nuclei /usr/local/bin/ && \
    nuclei -ut  # update nuclei templates

# Non-root user
RUN useradd --create-home --shell /bin/bash vixor \
    && chown -R vixor:vixor /app /root/.local /root/.cache
USER vixor

# Default: sleep so the container can be used as a sidecar for task execution
CMD ["sleep", "infinity"]
