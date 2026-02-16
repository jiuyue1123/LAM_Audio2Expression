# LAM-A2E API Server

[![Apache License](https://img.shields.io/badge/📃-Apache--2.0-929292)](https://www.apache.org/licenses/LICENSE-2.0)

## 简介

本项目是基于 [aigc3d/LAM_Audio2Expression](https://github.com/aigc3d/LAM_Audio2Expression) 的 fork 版本，专注于提供 HTTP API 服务。

### 主要改动

- ✨ **新增 FastAPI HTTP 接口和其测试脚本** (`api_server.py` `test_api.py`) - 提供远程推理能力
- 🌐 **REST API 服务** - 支持标准推理和流式推理两种模式
- 🐳 **Docker 支持** - 容器化部署配置
- 📝 **完整 API 文档** - 详细的接口说明和示例
- ❌ **移除本地调用入口** - 专注于 API 服务

### 核心功能

- 🎯 **ARKit 标准输出**: 生成 52 个标准 ARKit blendshape 表情参数
- ⚡ **实时流式推理**: 支持音频流式处理，适合实时应用
- 🎬 **完整音频推理**: 支持处理完整音频文件
- 🔧 **可配置后处理**: 支持嘴部平滑、眉毛运动、随机眨眼等
- 🎨 **多风格支持**: 通过 `id_idx` (0-11) 选择不同表情风格

## 项目结构

```
LAM_Audio2Expression/
├── api_server.py              # FastAPI 服务器入口
├── configs/                   # 配置文件
│   ├── lam_audio2exp_config_streaming.py
│   └── wav2vec2_config.json
├── engines/                   # 推理引擎
│   ├── defaults.py           # 默认配置和设置
│   └── infer.py              # 推理逻辑
├── models/                    # 模型定义
│   ├── network.py            # Audio2Expression 网络
│   ├── utils.py              # Blendshape 工具函数
│   ├── encoder/              # 音频编码器
│   └── losses/               # 损失函数
|—— scripts/                   # 脚本
├── utils/                     # 工具函数
├── requirements.txt           # Python 依赖
├── requirements_api.txt       # API 服务器依赖
├── Dockerfile                 # Docker 构建文件
└── test_api.py               # API 测试脚本
```

## 安装和使用

> 📝 **注意**: 详细的安装和使用说明请参考原项目 [aigc3d/LAM_Audio2Expression](https://github.com/aigc3d/LAM_Audio2Expression) 或根据您的部署环境自行配置。

### 基本要求
- [huggingface_hub cli](https://hugging-face.cn/docs/huggingface_hub/guides/cli)
- Python 3.10
- CUDA ≥ 11.8 （GPU 加速）
- 4GB+ GPU 显存（推荐）

## 本地部署

### 准备环境

```bash
# 克隆项目仓库
git clone https://github.com/jiuyue1123/LAM_Audio2Expression.git
# 进入项目目录
cd LAM_Audio2Expression

# 创建conda虚拟环境（当前仅支持Python 3.10版本）
conda create -n lam_a2e python=3.10

# 激活该conda虚拟环境
conda activate lam_a2e

# 安装依赖（linux）
## 基于CUDA 12.1版本安装依赖
./scripts/install/install_cu121.bat

## 或者，基于CUDA 11.8版本安装依赖
./scripts/install/install_cu118.bat

# 安装依赖（linux）
## 基于CUDA 12.1版本安装依赖
sh  ./scripts/install/install_cu121.sh

## 或者，基于CUDA 11.8版本安装依赖
sh ./scripts/install/install_cu118.sh

# 下载模型（本地和Docker部署只需要下载一次）
hf download 3DAIGC/LAM_audio2exp --local-dir ./ --exclude README.md 
tar -xzvf LAM_audio2exp_assets.tar && rm -f LAM_audio2exp_assets.tar
tar -xzvf LAM_audio2exp_streaming.tar && rm -f LAM_audio2exp_streaming.tar
```

## Docker 部署

### 构建镜像

```bash
# 克隆项目仓库
git clone https://github.com/jiuyue1123/LAM_Audio2Expression.git
# 进入项目目录
cd LAM_Audio2Expression

# 下载模型（本地和Docker部署只需要下载一次）
hf download 3DAIGC/LAM_audio2exp --local-dir ./ --exclude README.md
tar -xzvf LAM_audio2exp_assets.tar && rm -f LAM_audio2exp_assets.tar
tar -xzvf LAM_audio2exp_streaming.tar && rm -f LAM_audio2exp_streaming.tar

# 构建镜像
docker build -t lam-a2e-api .
```

### 运行容器

```bash
docker run --rm \
  --gpus all \
  -p 8000:8000 \
  lam-a2e-api
```

## 使用方式

见[API文档](./docs/API_DOCUMENTATION.md)

测试功能：

```bash
# 全部功能测试
python test_api.py

# 基础功能测试
python test_api.py --test basic

# 流式推理测试
python test_api.py --test streaming

# 性能测试
python test_api.py --test performance

支持参数：
--host localhost --port 8000
```

## 性能优化

### 推荐配置

- GPU: NVIDIA RTX 3060 或更高
- 显存: 8GB+
- CPU: 8 核心+
- 内存: 16GB+

### 优化建议

1. 使用 GPU 加速（自动检测）
2. 批量处理多个音频文件
3. 对于实时应用，使用流式推理模式
4. 调整 `id_idx` 参数以获得不同风格

## 常见问题

### Q: 如何选择 id_idx？

A: `id_idx` 范围是 0-11，不同的值会产生不同的表情风格。建议尝试多个值找到最适合的。

### Q: 流式推理的音频块应该多长？

A: 推荐 1-2 秒的音频块。太短可能导致表情不连贯，太长会增加延迟。

### Q: 如何提高推理速度？

A:

1. 使用 GPU
2. 设置 `ex_vol=false`（跳过人声提取）
3. 设置 `movement_smooth=false` 和 `brow_movement=false`

## 相关项目

- [LAM](https://github.com/aigc3d/LAM) - Large Avatar Model
- [LAM_Audio2Expression](https://github.com/aigc3d/LAM_Audio2Expression) - 原始项目
- [Three.js](https://threejs.org/) - 3D 渲染库
- [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) - VRM 加载器

## 许可证

本项目采用 Apache License 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

## 引用

如果您在研究中使用了本项目，请引用：

```bibtex
@inproceedings{he2025LAM,
  title={LAM: Large Avatar Model for One-shot Animatable Gaussian Head},
  author={
    Yisheng He and Xiaodong Gu and Xiaodan Ye and Chao Xu and Zhengyi Zhao and Yuan Dong and Weihao Yuan and Zilong Dong and Liefeng Bo
  },
  booktitle={arXiv preprint arXiv:2502.17796},
  year={2025}
}
```
