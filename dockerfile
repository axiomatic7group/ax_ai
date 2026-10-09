FROM python:3.12-slim AS builder

WORKDIR /


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    cmake \
    git \
    libcurl4-openssl-dev \
    libssl-dev \
    libgomp1\
    curl\
    supervisor\
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/ggml-org/llama.cpp.git && \
    cd llama.cpp

WORKDIR /llama.cpp
RUN cmake -B build -DLLAMA_CURL=ON -DLLAMA_OPENSSL=ON && \
    cmake --build build --config Release

WORKDIR /build-env
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt



FROM python:3.12-slim

WORKDIR /ax_ai

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1\
    supervisor && rm -rf /var/lib/apt/lists/*\
    && ldconfig


COPY --from=builder /install /usr/local
COPY --from=builder /llama.cpp/build/bin/llama-server /usr/local/bin/
COPY --from=builder /llama.cpp/build/bin/lib*.so* /usr/lib/

COPY ax_ai/ .
COPY entrypoint.sh ./entrypoint.sh
COPY supervisord.conf /etc/supervisor/supervisord.conf

RUN useradd -m -s /bin/sh appuser
RUN mkdir -p /ax_ai/db_data && \
    chown -R appuser:appuser /ax_ai &&\
    mkdir -p /var/log/supervisor /var/run/supervisor \
    && chown -R appuser:appuser /var/log/supervisor /var/run/supervisor

USER appuser

EXPOSE 8000 8080

ENTRYPOINT ["./entrypoint.sh"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
