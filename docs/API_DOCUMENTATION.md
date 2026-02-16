# LAM-A2E API 文档

## 概述

LAM-A2E API 提供音频到面部表情的实时推理服务，支持标准推理和流式推理两种模式。

- **基础URL**: `http://localhost:8000`
- **协议**: HTTP/REST
- **数据格式**: JSON, multipart/form-data

---

## 服务器启动

### 启动命令

```bash
python api_server.py [OPTIONS]
```

### 启动参数

| 参数            | 类型   | 默认值                                      | 说明                                     |
| --------------- | ------ | ------------------------------------------- | ---------------------------------------- |
| `--host`        | string | `0.0.0.0`                                   | 服务器绑定的主机地址                     |
| `--port`        | int    | `8000`                                      | 服务器监听端口                           |
| `--config-file` | string | `configs/lam_audio2exp_config_streaming.py` | 模型配置文件路径                         |
| `--weight`      | string | `None`                                      | 模型权重文件路径（覆盖配置文件中的设置） |

### 启动示例

```bash
# 默认启动
python api_server.py

# 自定义端口
python api_server.py --port 9000

# 指定模型权重
python api_server.py --weight pretrained_models/lam_audio2exp_streaming.tar

# 完整配置
python api_server.py --host 0.0.0.0 --port 8000 --config-file configs/lam_audio2exp_config_streaming.py
```

---

## API 接口

### 1. 根路径

**端点**: `GET /`

**描述**: 获取API服务信息和可用端点列表

**请求**: 无参数

**响应示例**:

```json
{
  "service": "LAM-A2E API",
  "version": "1.0.0",
  "endpoints": {
    "infer": "/api/infer",
    "stream_init": "/api/infer_stream_init",
    "stream_chunk": "/api/infer_stream_chunk",
    "health": "/api/health"
  }
}
```

---

### 2. 健康检查

**端点**: `GET /api/health`

**描述**: 检查服务器状态和资源可用性

**请求**: 无参数

**响应字段**:

| 字段　　　　　　 | 类型　　 | 说明　　　　　　　　　　　　　　　  |
| ---------------- | -------- | ----------------------------------- |
| `status`　　　　 | string　 | 服务状态：`healthy` 或 `not_ready`  |
| `model_loaded`　 | boolean  | 模型是否已加载　　　　　　　　　　  |
| `gpu_available`  | boolean  | GPU是否可用　　　　　　　　　　　　 |
| `sessions`　　　 | integer  | 当前活跃的流式会话数量　　　　　　  |

**响应示例**:

```json
{
  "status": "healthy",
  "model_loaded": true,
  "gpu_available": true,
  "sessions": 2
}
```

**cURL 示例**:

```bash
curl -X GET "http://localhost:8000/api/health"
```

---

### 3. 标准推理（完整音频）

**端点**: `POST /api/infer`

**描述**: 处理完整音频文件，生成完整的面部表情动画数据

**Content-Type**: `multipart/form-data`

**请求参数**:

| 参数　　　　　　　 | 类型　　 | 必填   | 默认值　 | 说明　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　 |
| ------------------ | -------- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------ |
| `audio_file`　　　 | File　　 | ✅　　 | -　　　  | 音频文件（支持WAV、MP3等格式）<br>推荐：16kHz采样率，单声道　　　　　　　　　　　　　　　　　　　　　　　　　　　  |
| `id_idx`　　　　　 | integer  | ❌　　 | `0`　　  | 身份索引，用于风格控制<br>范围：0-11（streaming模型）<br>不同的ID会产生不同的表情风格　　　　　　　　　　　　　　  |
| `ex_vol`　　　　　 | boolean  | ❌　　 | `false`  | 是否提取人声轨道<br>`true`: 使用spleeter分离人声（适合有背景音乐的音频，但速度较慢）<br>`false`: 直接使用原始音频  |
| `movement_smooth`  | boolean  | ❌　　 | `false`  | 是否应用嘴部动作平滑<br>`true`: 在静音期间减少嘴部动作，使动画更自然<br>`false`: 不进行额外平滑处理　　　　　　　  |
| `brow_movement`　  | boolean  | ❌　　 | `false`  | 是否添加随机眉毛动作<br>`true`: 根据音频音量自动添加眉毛表情<br>`false`: 不添加额外眉毛动作　　　　　　　　　　　  |

**响应字段**:

| 字段　　　　　　　　　　　　 | 类型　　　　　 | 说明　　　　　　　　　　　　　　 |
| ---------------------------- | -------------- | -------------------------------- |
| `names`　　　　　　　　　　  | array[string]  | 52个ARKit blendshape名称列表　　 |
| `metadata`　　　　　　　　　 | object　　　　 | 元数据信息　　　　　　　　　　　 |
| `metadata.fps`　　　　　　　 | float　　　　  | 帧率（固定30.0）　　　　　　　　 |
| `metadata.frame_count`　　　 | integer　　　  | 总帧数　　　　　　　　　　　　　 |
| `metadata.blendshape_count`  | integer　　　  | Blendshape数量（固定52）　　　　 |
| `metadata.inference_time`　  | float　　　　  | 推理耗时（秒）　　　　　　　　　 |
| `frames`　　　　　　　　　　 | array[object]  | 每一帧的数据　　　　　　　　　　 |
| `frames[].weights`　　　　　 | array[float]　 | 52个blendshape权重值（0.0-1.0）  |
| `frames[].time`　　　　　　  | float　　　　  | 时间（秒）　　　　　　　　　　　 |
| `frames[].rotation`　　　　  | array[float]　 | 头部旋转数据（当前为空）　　　　 |

**ARKit Blendshape 名称列表**:

```json
{
  "names": [
    "browDownLeft",
    "browDownRight",
    "browInnerUp",
    "browOuterUpLeft",
    "browOuterUpRight",
    "cheekPuff",
    "cheekSquintLeft",
    "cheekSquintRight",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "eyeLookDownLeft",
    "eyeLookDownRight",
    "eyeLookInLeft",
    "eyeLookInRight",
    "eyeLookOutLeft",
    "eyeLookOutRight",
    "eyeLookUpLeft",
    "eyeLookUpRight",
    "eyeSquintLeft",
    "eyeSquintRight",
    "eyeWideLeft",
    "eyeWideRight",
    "jawForward",
    "jawLeft",
    "jawOpen",
    "jawRight",
    "mouthClose",
    "mouthDimpleLeft",
    "mouthDimpleRight",
    "mouthFrownLeft",
    "mouthFrownRight",
    "mouthFunnel",
    "mouthLeft",
    "mouthLowerDownLeft",
    "mouthLowerDownRight",
    "mouthPressLeft",
    "mouthPressRight",
    "mouthPucker",
    "mouthRight",
    "mouthRollLower",
    "mouthRollUpper",
    "mouthShrugLower",
    "mouthShrugUpper",
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthStretchLeft",
    "mouthStretchRight",
    "mouthUpperUpLeft",
    "mouthUpperUpRight",
    "noseSneerLeft",
    "noseSneerRight",
    "tongueOut"
  ]
}
```

**响应示例**:

```json
{
  "names": ["browDownLeft", "browDownRight", ...],
  "metadata": {
    "fps": 30.0,
    "frame_count": 150,
    "blendshape_count": 52,
    "inference_time": 0.3822023868560791
  },
  "frames": [
    {
      "weights": [0.05, 0.03, 0.12, ..., 0.0],
      "time": 0.0,
      "rotation": []
    },
    {
      "weights": [0.06, 0.04, 0.15, ..., 0.0],
      "time": 0.03333333333333333,
      "rotation": []
    }
  ]
}
```

**curl 示例**:

```bash
# 基本调用
curl -X POST "http://localhost:8000/api/infer" \
  -F "audio_file=@test.wav"

# 完整参数
curl -X POST "http://localhost:8000/api/infer" \
  -F "audio_file=@speech.wav" \
  -F "id_idx=3" \
  -F "ex_vol=false" \
  -F "movement_smooth=true" \
  -F "brow_movement=true"

# 保存结果到文件
curl -X POST "http://localhost:8000/api/infer" \
  -F "audio_file=@test.wav" \
  -F "movement_smooth=true" \
  -o result.json
```

**Python 示例**:

```python
import requests

url = "http://localhost:8000/api/infer"

# 准备文件和参数
files = {
    'audio_file': open('test.wav', 'rb')
}
data = {
    'id_idx': 0,
    'ex_vol': False,
    'movement_smooth': True,
    'brow_movement': True
}

# 发送请求
response = requests.post(url, files=files, data=data)
result = response.json()

print(f"生成了 {result['metadata']['frame_count']} 帧动画")
print(f"推理耗时: {result['metadata']['inference_time']:.2f} 秒")
```

**错误响应**:

| HTTP状态码  | 说明　　　　　　　　　　 |
| ----------- | ------------------------ |
| `400`　　　 | 音频文件无效或格式不支持 |
| `500`　　　 | 推理过程出错　　　　　　 |
| `503`　　　 | 模型未初始化　　　　　　 |

---

### 4. 初始化流式会话

**端点**: `POST /api/infer_stream_init`

**描述**: 创建一个新的流式推理会话，用于实时处理音频流

**Content-Type**: `application/json`

**请求参数**:

| 参数　　 | 类型　　 | 必填   | 默认值  | 说明　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　 |
| -------- | -------- | ------ | ------- | -------------------------------------------------------------------------- |
| `id_idx` | integer  | ❌　　 | `0`　　 | 身份索引，用于风格控制<br>范围：0-11（streaming模型）<br>会话期间保持不变  |

**请求示例**:

```json
{
  "id_idx": 0
}
```

**响应字段**:

| 字段         | 类型    | 说明                                                  |
| ------------ | ------- | ----------------------------------------------------- |
| `session_id` | string  | 会话唯一标识符（UUID格式）<br>用于后续的chunk处理请求 |
| `message`    | string  | 状态消息                                              |
| `id_idx`     | integer | 确认的身份索引                                        |

**响应示例**:

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Streaming session initialized",
  "id_idx": 0
}
```

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/api/infer_stream_init" \
  -H "Content-Type: application/json" \
  -d '{"id_idx": 0}'
```

**Python 示例**:

```python
import requests

url = "http://localhost:8000/api/infer_stream_init"
payload = {"id_idx": 0}

response = requests.post(url, json=payload)
session_data = response.json()
session_id = session_data['session_id']

print(f"会话ID: {session_id}")
```

**注意事项**:

- 每个会话独立维护上下文状态
- 会话会保持在服务器内存中直到显式关闭或服务器重启
- 建议在使用完毕后调用关闭接口释放资源

---

### 5. 处理流式音频块

**端点**: `POST /api/infer_stream_chunk`

**描述**: 处理单个音频块（约1秒），返回对应的表情数据，适合处理长音频

**Content-Type**: `multipart/form-data`

**请求参数**:

| 参数　　　　　 | 类型　 | 必填   | 默认值  | 说明　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　 |
| -------------- | ------ | ------ | ------- | ------------------------------------------------------------------------------ |
| `session_id`　 | string | ✅　　 | -　　　 | 会话ID（从init接口获取）<br>格式：UUID字符串　　　　　　　　　　　　　　　　　 |
| `audio_chunk`  | File　 | ✅　　 | -　　　 | 音频块文件<br>推荐：1秒长度，16kHz采样率，单声道WAV格式<br>可以是0.5-2秒的音频 |

**响应字段**:

| 字段　　　　　　　　　　　　 | 类型　　　　　 | 说明　　　　　　　　　　　　　　 |
| ---------------------------- | -------------- | -------------------------------- |
| `names`　　　　　　　　　　  | array[string]  | 52个ARKit blendshape名称列表　　 |
| `metadata`　　　　　　　　　 | object　　　　 | 元数据信息　　　　　　　　　　　 |
| `metadata.fps`　　　　　　　 | float　　　　  | 帧率（固定30.0）　　　　　　　　 |
| `metadata.frame_count`　　　 | integer　　　  | 本次chunk的帧数（约30帧）　　　  |
| `metadata.blendshape_count`  | integer　　　  | Blendshape数量（固定52）　　　　 |
| `metadata.session_id`　　　  | string　　　　 | 会话ID　　　　　　　　　　　　　 |
| `metadata.chunk_index`　　　 | integer　　　  | 当前chunk序号（从1开始）　　　　 |
| `metadata.inference_time`　  | float　　　　  | 本次推理耗时（秒）　　　　　　　 |
| `frames`　　　　　　　　　　 | array[object]  | 每一帧的数据　　　　　　　　　　 |
| `frames[].weights`　　　　　 | array[float]　 | 52个blendshape权重值（0.0-1.0）  |
| `frames[].time`　　　　　　  | float　　　　  | 相对时间戳（秒）　　　　　　　　 |
| `frames[].rotation`　　　　  | array[float]　 | 头部旋转数据（当前为空）　　　　 |

**响应示例**:

```json
{
  "names": ["browDownLeft", "browDownRight", ...],
  "metadata": {
    "fps": 30.0,
    "frame_count": 30,
    "blendshape_count": 52,
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "chunk_index": 1,
    "inference_time": 0.085
  },
  "frames": [
    {
      "weights": [0.05, 0.03, 0.12, ..., 0.0],
      "time": 0.0,
      "rotation": []
    },
    ...
  ]
}
```

**cURL 示例**:

```bash
# 处理第一个chunk
curl -X POST "http://localhost:8000/api/infer_stream_chunk" \
  -F "session_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -F "audio_chunk=@chunk_001.wav"

# 处理后续chunk
curl -X POST "http://localhost:8000/api/infer_stream_chunk" \
  -F "session_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -F "audio_chunk=@chunk_002.wav"
```

**Python 完整流式示例**:

```python
import requests
import numpy as np
import soundfile as sf

# 1. 初始化会话
init_url = "http://localhost:8000/api/infer_stream_init"
response = requests.post(init_url, json={"id_idx": 0})
session_id = response.json()['session_id']

# 2. 加载完整音频
audio, sr = sf.read('long_audio.wav')

# 3. 分块处理
chunk_url = "http://localhost:8000/api/infer_stream_chunk"
chunk_size = sr  # 1秒
all_results = []

for i in range(0, len(audio), chunk_size):
    # 提取音频块
    chunk = audio[i:i+chunk_size]

    # 保存临时文件
    chunk_file = f'temp_chunk_{i}.wav'
    sf.write(chunk_file, chunk, sr)

    # 发送请求
    files = {'audio_chunk': open(chunk_file, 'rb')}
    data = {'session_id': session_id}
    response = requests.post(chunk_url, files=files, data=data)

    result = response.json()
    all_results.append(result)
    print(f"处理chunk {result['metadata']['chunk_index']}, "
          f"耗时: {result['metadata']['inference_time']:.3f}秒")

# 4. 关闭会话
close_url = f"http://localhost:8000/api/infer_stream_close/{session_id}"
requests.delete(close_url)

print(f"总共处理 {len(all_results)} 个音频块")
```

**错误响应**:

| HTTP状态码 | 说明         |
| ---------- | ------------ |
| `400`      | 音频块无效   |
| `404`      | 会话ID不存在 |
| `500`      | 推理过程出错 |
| `503`      | 模型未初始化 |

**注意事项**:

- 音频块应按顺序发送，以保持上下文连续性
- 每个chunk的推理会利用前一个chunk的上下文信息
- 推荐chunk长度为1秒（16000个采样点@16kHz）

---

### 6. 关闭流式会话

**端点**: `DELETE /api/infer_stream_close/{session_id}`

**描述**: 关闭指定的流式会话，释放服务器资源

**路径参数**:

| 参数         | 类型   | 必填 | 说明           |
| ------------ | ------ | ---- | -------------- |
| `session_id` | string | ✅   | 要关闭的会话ID |

**响应字段**:

| 字段　　　　  | 类型　 | 说明　　　　　 |
| ------------- | ------ | -------------- |
| `message`　　 | string | 状态消息　　　 |
| `session_id`  | string | 已关闭的会话ID |

**响应示例**:

```json
{
  "message": "Session closed",
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**cURL 示例**:

```bash
curl -X DELETE "http://localhost:8000/api/infer_stream_close/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**Python 示例**:

```python
import requests

session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
url = f"http://localhost:8000/api/infer_stream_close/{session_id}"

response = requests.delete(url)
print(response.json()['message'])
```

**错误响应**:

| HTTP状态码  | 说明　　　　 |
| ----------- | ------------ |
| `404`　　　 | 会话ID不存在 |

---

## 使用场景

### 场景1：离线音频处理

适用于：视频配音、动画制作、批量处理

```python
import requests

# 处理单个音频文件
files = {'audio_file': open('speech.wav', 'rb')}
data = {
    'id_idx': 0,
    'movement_smooth': True,
    'brow_movement': True
}

response = requests.post(
    'http://localhost:8000/api/infer',
    files=files,
    data=data
)

# 保存结果
with open('animation.json', 'w') as f:
    json.dump(response.json(), f)
```

### 场景2：实时对话系统

适用于：虚拟主播、数字人对话、实时互动

```python
import requests
import pyaudio
import numpy as np

# 初始化会话
session = requests.post(
    'http://localhost:8000/api/infer_stream_init',
    json={'id_idx': 0}
).json()
session_id = session['session_id']

# 实时录音并处理
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1,
                rate=16000, input=True, frames_per_buffer=16000)

try:
    while True:
        # 录制1秒音频
        audio_data = stream.read(16000)

        # 发送处理
        files = {'audio_chunk': ('chunk.wav', audio_data)}
        data = {'session_id': session_id}

        response = requests.post(
            'http://localhost:8000/api/infer_stream_chunk',
            files=files,
            data=data
        )

        # 使用返回的blendshape驱动3D模型
        blendshapes = response.json()
        # ... 渲染逻辑 ...

finally:
    # 清理
    stream.close()
    requests.delete(f'http://localhost:8000/api/infer_stream_close/{session_id}')
```

### 场景3：批量文件处理

```python
import requests
from pathlib import Path

audio_dir = Path('audio_files')
output_dir = Path('results')
output_dir.mkdir(exist_ok=True)

for audio_file in audio_dir.glob('*.wav'):
    print(f"处理: {audio_file.name}")

    files = {'audio_file': open(audio_file, 'rb')}
    data = {'movement_smooth': True}

    response = requests.post(
        'http://localhost:8000/api/infer',
        files=files,
        data=data
    )

    # 保存结果
    output_file = output_dir / f"{audio_file.stem}.json"
    with open(output_file, 'w') as f:
        json.dump(response.json(), f)
```

## 错误处理

### 常见错误码

| 状态码 | 错误类型              | 可能原因           | 解决方案               |
| ------ | --------------------- | ------------------ | ---------------------- |
| 400    | Bad Request           | 音频文件格式不支持 | 转换为WAV格式          |
| 404    | Not Found             | 会话ID不存在       | 检查session_id是否正确 |
| 500    | Internal Server Error | 推理过程异常       | 检查服务器日志         |
| 503    | Service Unavailable   | 模型未加载         | 等待模型加载完成       |

### 错误响应格式

```json
{
  "detail": "错误详细信息"
}
```

---

## 最佳实践

### 1. 音频格式建议

- 采样率：16kHz
- 声道：单声道（mono）
- 格式：WAV（PCM）
- 比特深度：16-bit

### 2. 参数选择建议

| 场景       | id_idx | movement_smooth | brow_movement | ex_vol |
| ---------- | ------ | --------------- | ------------- | ------ |
| 清晰语音   | 0      | true            | true          | false  |
| 带背景音乐 | 0      | true            | true          | true   |
| 快速处理   | 0      | false           | false         | false  |
| 高质量动画 | 0-11   | true            | true          | false  |

### 3. 性能优化

- 使用流式推理降低延迟
- 批量处理时复用会话
- 预处理音频格式避免实时转换
- 合理设置并发数避免GPU过载

### 4. 资源管理

- 及时关闭不用的流式会话
- 监控GPU显存使用情况
- 设置请求超时时间
- 实现请求队列避免过载

---

## 技术支持

### 日志查看

服务器日志会输出到控制台，包含：

- 模型加载状态
- 请求处理信息
- 错误堆栈信息

### 调试模式

```bash
# 启动时查看详细日志
python api_server.py --log-level debug
```

### 常见问题

**Q: 推理速度慢怎么办？**
A:

1. 确保使用GPU（检查 `/api/health` 的 `gpu_available`）
2. 使用流式推理模式
3. 关闭 `ex_vol` 选项
4. 减少音频时长

**Q: 如何支持多用户并发？**
A:

1. 每个用户使用独立的流式会话
2. 根据GPU显存限制并发数
3. 实现请求队列机制

**Q: 如何提高动画质量？**
A:

1. 使用高质量音频输入
2. 开启 `movement_smooth` 和 `brow_movement`
3. 尝试不同的 `id_idx` 值
4. 使用 `ex_vol` 提取纯人声
