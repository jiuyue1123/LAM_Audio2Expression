"""
LAM-A2E API Server
Provides REST API for audio-to-expression inference

Usage:
    python api_server.py --config-file configs/lam_audio2exp_config_streaming.py

API Endpoints:
    POST /api/infer - Standard inference with complete audio
    POST /api/infer_stream_init - Initialize streaming session
    POST /api/infer_stream_chunk - Process audio chunk in streaming mode
    GET /api/health - Health check
"""

from contextlib import asynccontextmanager
import os
import uuid
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import librosa
import torch
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engines.defaults import (
    default_argument_parser,
    default_config_parser,
    default_setup,
)
from engines.infer import INFER
from models.utils import export_blendshape_animation, ARKitBlendShape

# ============= Data Models =============
class InferRequest(BaseModel):
    id_idx: Optional[int] = 0
    ex_vol: Optional[bool] = False
    movement_smooth: Optional[bool] = False
    brow_movement: Optional[bool] = False


class StreamInitRequest(BaseModel):
    id_idx: Optional[int] = 0


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    gpu_available: bool
    sessions: int

# ============= Startup & Shutdown =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # ===== Startup =====
    config_file = os.getenv(
        "CONFIG_FILE",
        "configs/lam_audio2exp_config_streaming.py"
    )
    weight_path = os.getenv("WEIGHT_PATH", None)
    
    print("=" * 60)
    print("Starting LAM-A2E API Server...")
    print("=" * 60)
    
    try:
        initialize_model(config_file, weight_path)
        print("✓ Server ready to accept requests")
    except Exception as e:
        print(f"✗ Failed to initialize model: {e}")
        print("Server will start but inference endpoints will return 503")
    
    yield  # 服务器运行期间
    
    # ===== Shutdown =====
    print("Shutting down LAM-A2E API Server...")
    streaming_sessions.clear()

# ============= Global State =============
app = FastAPI(title="LAM-A2E API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
model_instance = None
config = None

# Session management for streaming
streaming_sessions: Dict[str, Dict[str, Any]] = {}


# ============= Initialization =============
def initialize_model(config_file: str, weight_path: Optional[str] = None):
    """Initialize the inference model at startup"""
    global model_instance, config
    
    args = default_argument_parser().parse_args([
        '--config-file', config_file
    ])
    
    config = default_config_parser(args.config_file, args.options)
    
    if weight_path:
        config.weight = weight_path
    
    config = default_setup(config)
    
    # Build model
    model_instance = INFER.build(dict(type=config.infer.type, cfg=config))
    model_instance.model.eval()
    
    print(f"✓ Model loaded from: {config.weight}")
    print(f"✓ Model ready for inference")


# ============= Helper Functions =============
def save_uploaded_audio(upload_file: UploadFile) -> str:
    """Save uploaded audio to temporary file"""
    suffix = Path(upload_file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = upload_file.file.read()
        tmp.write(content)
        return tmp.name


def load_and_validate_audio(file_path: str) -> tuple:
    """Load audio and validate format"""
    try:
        audio, sr = librosa.load(file_path, sr=16000)
        return audio, sr
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio file: {str(e)}")


def blendshapes_to_json(blendshapes: np.ndarray, fps: float = 30.0) -> dict:
    """Convert blendshape array to JSON format"""
    return {
        "names": ARKitBlendShape,
        "metadata": {
            "fps": fps,
            "frame_count": len(blendshapes),
            "blendshape_count": 52
        },
        "frames": [
            {
                "weights": blendshapes[i].tolist(),
                "time": i / fps,
                "rotation": []
            }
            for i in range(len(blendshapes))
        ]
    }


# ============= API Endpoints =============
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LAM-A2E API",
        "version": "1.0.0",
        "endpoints": {
            "infer": "/api/infer",
            "stream_init": "/api/infer_stream_init",
            "stream_chunk": "/api/infer_stream_chunk",
            "health": "/api/health"
        }
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if model_instance else "not_ready",
        model_loaded=model_instance is not None,
        gpu_available=torch.cuda.is_available(),
        sessions=len(streaming_sessions)
    )


@app.post("/api/infer")
async def infer(
    audio_file: UploadFile = File(...),
    id_idx: int = Form(0),
    ex_vol: bool = Form(False),
    movement_smooth: bool = Form(False),
    brow_movement: bool = Form(False)
):
    """
    Standard inference endpoint for complete audio file
    
    Args:
        audio_file: Audio file (WAV, MP3, etc.)
        id_idx: Identity index for style control (0-11 for streaming model)
        ex_vol: Extract vocal track (slower but better for music)
        movement_smooth: Apply mouth movement smoothing
        brow_movement: Add random brow movements
    
    Returns:
        JSON with blendshape animation data
    """
    if model_instance is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    temp_audio_path = None
    temp_vocal_path = None
    
    try:
        start_time = time.time()
        
        # Save uploaded file
        temp_audio_path = save_uploaded_audio(audio_file)
        
        # Load and validate audio
        audio, sr = load_and_validate_audio(temp_audio_path)
        
        # Extract vocals if requested
        if ex_vol:
            vocal_path = model_instance.extract_vocal_track(temp_audio_path)
            if os.path.exists(vocal_path):
                temp_vocal_path = vocal_path
                audio, sr = librosa.load(vocal_path, sr=16000)
        
        # Prepare input
        input_dict = {
            'id_idx': torch.nn.functional.one_hot(
                torch.tensor(id_idx),
                config.model.backbone.num_identity_classes
            ).cuda(non_blocking=True)[None, ...],
            'input_audio_array': torch.FloatTensor(audio).cuda(non_blocking=True)[None, ...]
        }
        
        # Run inference
        with torch.no_grad():
            output_dict = model_instance.model(input_dict)
        
        # Get output expression
        out_exp = output_dict['pred_exp'].squeeze().cpu().numpy()
        
        # Calculate volume for post-processing
        frame_length = int(len(audio) / sr * 30)
        volume = librosa.feature.rms(
            y=audio,
            frame_length=int(1 / 30 * sr),
            hop_length=int(1 / 30 * sr)
        )[0]
        if len(volume) > frame_length:
            volume = volume[:frame_length]
        
        # Apply post-processing
        if movement_smooth:
            from models.utils import smooth_mouth_movements
            out_exp = smooth_mouth_movements(out_exp, 0, volume)
        
        if brow_movement:
            from models.utils import apply_random_brow_movement
            out_exp = apply_random_brow_movement(out_exp, volume)
        
        # Standard post-processing
        pred_exp = model_instance.blendshape_postprocess(out_exp)
        
        # Convert to JSON
        result = blendshapes_to_json(pred_exp, fps=30.0)
        
        inference_time = time.time() - start_time
        result["metadata"]["inference_time"] = inference_time
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
    
    finally:
        # Cleanup temporary files
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        if temp_vocal_path and os.path.exists(temp_vocal_path):
            import shutil
            shutil.rmtree(os.path.dirname(temp_vocal_path), ignore_errors=True)


@app.post("/api/infer_stream_init")
async def infer_stream_init(request: StreamInitRequest):
    """
    Initialize a streaming inference session
    
    Args:
        id_idx: Identity index for style control
    
    Returns:
        session_id for subsequent chunk processing
    """
    if model_instance is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    session_id = str(uuid.uuid4())
    
    streaming_sessions[session_id] = {
        "id_idx": request.id_idx,
        "context": {
            'is_initial_input': True,
            'previous_audio': None,
            'previous_expression': None,
            'previous_volume': None,
            'previous_headpose': None,
        },
        "created_at": time.time(),
        "chunk_count": 0
    }
    
    return {
        "session_id": session_id,
        "message": "Streaming session initialized",
        "id_idx": request.id_idx
    }


@app.post("/api/infer_stream_chunk")
async def infer_stream_chunk(
    session_id: str = Form(...),
    audio_chunk: UploadFile = File(...)
):
    """
    Process audio chunk in streaming mode
    
    Args:
        session_id: Session ID from init endpoint
        audio_chunk: Audio chunk (approximately 1 second, 16kHz)
    
    Returns:
        Blendshape data for this chunk
    """
    if model_instance is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    if session_id not in streaming_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = streaming_sessions[session_id]
    temp_chunk_path = None
    
    try:
        start_time = time.time()
        
        # Save and load audio chunk
        temp_chunk_path = save_uploaded_audio(audio_chunk)
        audio, sr = load_and_validate_audio(temp_chunk_path)
        
        # Validate and limit audio chunk length
        # max_frame_length=64 corresponds to ~2.13 seconds at 16kHz
        # We limit to 2 seconds (32000 samples at 16kHz) to be safe
        max_audio_samples = int(sr * 2.0)  # 2 seconds max
        if len(audio) > max_audio_samples:
            audio = audio[:max_audio_samples]
        
        # Ensure minimum audio length (at least 0.1 seconds)
        min_audio_samples = int(sr * 0.1)
        if len(audio) < min_audio_samples:
            raise HTTPException(
                status_code=400,
                detail=f"Audio chunk too short: {len(audio)} samples, minimum {min_audio_samples} samples required"
            )
        
        # Run streaming inference
        output, context = model_instance.infer_streaming_audio(
            audio=audio,
            ssr=float(sr),
            context=session["context"]
        )
        
        # Check if inference was successful
        if output is None or output.get("code") != 0:
            error_code = output.get('code') if output else 'None'
            raise HTTPException(
                status_code=500, 
                detail=f"Inference failed with code: {error_code}"
            )
        
        # Validate output
        if output.get("expression") is None:
            raise HTTPException(
                status_code=500,
                detail="Inference returned no expression data"
            )
        
        # Update session context
        session["context"] = context
        session["chunk_count"] += 1
        
        # Convert to JSON
        result = blendshapes_to_json(output["expression"], fps=30.0)
        result["metadata"]["session_id"] = session_id
        result["metadata"]["chunk_index"] = session["chunk_count"]
        result["metadata"]["inference_time"] = time.time() - start_time
        result["metadata"]["audio_length"] = len(audio) / sr
        
        return JSONResponse(content=result)
        result["metadata"]["chunk_index"] = session["chunk_count"]
        result["metadata"]["inference_time"] = time.time() - start_time
        
        return JSONResponse(content=result)
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Streaming inference failed: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)
    
    finally:
        if temp_chunk_path and os.path.exists(temp_chunk_path):
            os.remove(temp_chunk_path)


@app.delete("/api/infer_stream_close/{session_id}")
async def infer_stream_close(session_id: str):
    """Close a streaming session and cleanup resources"""
    if session_id in streaming_sessions:
        del streaming_sessions[session_id]
        return {"message": "Session closed", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

# ============= Main Entry Point =============
if __name__ == "__main__":
    import uvicorn
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="LAM-A2E API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--config-file", type=str, 
                       default="configs/lam_audio2exp_config_streaming.py",
                       help="Model config file")
    parser.add_argument("--weight", type=str, default=None,
                       help="Model weight path (override config)")
    args = parser.parse_args()
    
    # Set environment variables for startup event
    os.environ["CONFIG_FILE"] = args.config_file
    if args.weight:
        os.environ["WEIGHT_PATH"] = args.weight
    
    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )
