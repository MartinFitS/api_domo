from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.faces import recibir_foto, train_model_function
router = APIRouter()

class ImageData(BaseModel):
    image_base64: str
    file_name: str

class ImageUploadRequest(BaseModel):
    username: str
    images: List[ImageData]

@router.post("/save_faces")
def save_faces(request: ImageUploadRequest):
    try:

        images_base64 = [image.image_base64 for image in request.images]

        recibir_foto(images_base64, request.username)

        return {"message": "Imágenes procesadas exitosamente", "total_faces": len(images_base64)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/entrenar")
def train_model():
    try:
        train_model_function()

        return {"message": "Modelo Entrenado"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
