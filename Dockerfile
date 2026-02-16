FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# 设置环境变量（提前设置，避免重复定义）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CONFIG_FILE=configs/lam_audio2exp_config_streaming.py \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 合并 RUN 指令减少层数，清理缓存减小体积
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    git \
    wget \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && apt-get clean

# 先单独复制 requirements，利用 Docker 缓存层
COPY requirements.txt .

# 安装依赖（合并为单层，先装 torch 再装其他依赖）
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip3 install --no-cache-dir -r requirements.txt

# 复制应用代码（按变更频率排序：先复制不常变的）
COPY configs/ ./configs/
COPY utils/ ./utils/
COPY engines/ ./engines/
COPY models/ ./models/
COPY pretrained_models/ ./pretrained_models/
COPY api_server.py .

# 创建目录并设置权限（使用非 root 用户提升安全性）
RUN mkdir -p pretrained_models assets/sample_audio && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

EXPOSE 8000

# 使用 exec 格式确保信号正确处理
CMD ["python3", "api_server.py", "--host", "0.0.0.0", "--port", "8000"]