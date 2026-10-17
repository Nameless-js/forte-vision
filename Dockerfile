# forte_ai engine + reference API server. Weights are downloaded in a build step; the container runs offline.
#
#   docker build -t forte-ai .
#   docker run --gpus all -p 8000:8000 -e FORTE_API_KEY=secret forte-ai
#
# Base image: CUDA 12.4 runtime (matches torch 2.6.0+cu124). For a CPU-only host build with
#   --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cpu --build-arg PROFILE=cpu
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ARG TORCH_INDEX=https://download.pytorch.org/whl/cu124
ARG PROFILE=gpu-small
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONUTF8=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends python3.12 python3.12-venv python3.12-dev python3-pip git curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && python3.12 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install --index-url ${TORCH_INDEX} torch==2.6.0 torchvision==0.21.0 \
    && grep -viE "^(torch|torchvision)==" requirements.txt > /tmp/req.txt \
    && pip install -r /tmp/req.txt

COPY forte_ai ./forte_ai
COPY server ./server
COPY configs ./configs
COPY kb ./kb
COPY scripts ./scripts
COPY data/labels.csv ./data/labels.csv
RUN pip install -e . --no-deps

# --- weights baked into the image (needs network at build time only) ---
ENV FORTE_MODELS_DIR=/app/models/hf
RUN python scripts/download_weights.py --profile ${PROFILE}

# --- offline from here on ---
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 FORTE_PROFILE=${PROFILE} \
    FORTE_DB_PATH=/data/jobs.sqlite3 FORTE_UPLOAD_DIR=/data/uploads FORTE_CACHE_DIR=/data/cache
VOLUME ["/data"]
EXPOSE 8000
COPY server/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
