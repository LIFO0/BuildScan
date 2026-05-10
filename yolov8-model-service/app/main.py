import io
import os
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

from app.schemas.predict import HealthResponse, PredictResponse
from app.services.predictor import YOLOPredictor


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as e:
        raise RuntimeError(f"Invalid {name}={value!r}, expected int") from e


MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "models", "best.pt"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.25"))
PORT = _get_env_int("PORT", 8001)

app = FastAPI(title="YOLOv8 Model Service", version="1.0.0")

_predictor: Optional[YOLOPredictor] = None
_startup_error: Optional[str] = None


@app.on_event("startup")
def _startup() -> None:
    global _predictor, _startup_error
    try:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
        _predictor = YOLOPredictor(model_path=MODEL_PATH, conf_threshold=CONFIDENCE_THRESHOLD)
        _startup_error = None
    except Exception as e:
        _predictor = None
        _startup_error = str(e)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok" if _predictor is not None else "error",
        model_loaded=_predictor is not None,
        service="yolov8-model-service",
        error=_startup_error,
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(...),
    visualize: bool = False,
) -> PredictResponse | Response:
    if _predictor is None:
        raise HTTPException(status_code=503, detail=f"Model not loaded: {_startup_error or 'unknown error'}")

    try:
        raw = await file.read()
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read image: {e}")

    result = _predictor.predict(image=image, return_visualization=visualize)

    if visualize and "visualization" in result and result["visualization"] is not None:
        buf = io.BytesIO()
        result["visualization"].save(buf, format="JPEG", quality=92)
        return Response(content=buf.getvalue(), media_type="image/jpeg")

    return PredictResponse.model_validate(result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=False)

