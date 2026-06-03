import io
import os
import uuid
import base64
from PIL import Image, ImageOps
from fastapi import HTTPException
from inference_sdk import InferenceHTTPClient
from app.config import settings

# Setup folder buat nyimpen gambar di dalam project lu
SAVE_DIR = "static/annotated_images"
os.makedirs(SAVE_DIR, exist_ok=True) # Bikin folder otomatis kalo belum ada

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=settings.ROBOFLOW_API_KEY
)

async def run_roboflow_workflow(image_bytes: bytes) -> dict:
    try:
        # Kirim bytes langsung sebagai base64. Jangan pakai PIL Image
        # karna library inference_sdk secara otomatis nge-resize/compress
        # gambar ke kotak kecil (640x640) jika inputnya berupa PIL Image.
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        raw_result = client.run_workflow(
            workspace_name=settings.ROBOFLOW_WORKSPACE,
            workflow_id=settings.ROBOFLOW_WORKFLOW,
            images={"image": base64_image},
            use_cache=True
        )
        
        if isinstance(raw_result, list) and len(raw_result) > 0:
            main_data = raw_result[0]
        elif isinstance(raw_result, dict) and "outputs" in raw_result:
            main_data = raw_result["outputs"][0]
        else:
            main_data = raw_result

        annotated_base64 = main_data.get("congestion_overlay_image")
        image_url = None
        
        if annotated_base64:
            if "," in annotated_base64:
                base64_data = annotated_base64.split(",")[1]
            else:
                base64_data = annotated_base64

            filename = f"hasil_deteksi_{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(SAVE_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(base64.b64decode(base64_data))


            image_url = f"/static/annotated_images/{filename}"

        return {
            "count_objects": main_data.get("count_objects"),
            "density_score": main_data.get("density_score"),
            "congestion_level": main_data.get("congestion_level"),
            "proximate_pairs": main_data.get("proximate_pairs"),
            "annotated_image_url": image_url 
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses lewat Roboflow SDK: {str(e)}"
        )