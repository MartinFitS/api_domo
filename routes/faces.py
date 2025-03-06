from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import jwt
import datetime
from bson import ObjectId
from services.faces import recibir_foto, train_model_function,recognize_face

router = APIRouter()


SECRET_KEY = "tu_secreto_super_seguro"
ALGORITHM = "HS256"

class FaceLoginRequest(BaseModel):
    img: str  

class ImageData(BaseModel):
    image_base64: str
    file_name: str

class ImageUploadRequest(BaseModel):
    username: str
    images: List[ImageData]

def create_jwt_token(user_data):
    user_id = str(user_data["_id"]) if "_id" in user_data else None
    safe_user_data = {k: v for k, v in user_data.items() if not isinstance(v, bytes)}

    payload = {
        "sub": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
        "user": safe_user_data
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

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


@router.post("/login/face")
async def login_face(request: FaceLoginRequest):
    try:
        user_data = recognize_face(request.img)  # Llamamos a la función de reconocimiento
        print(user_data)

           
        token = create_jwt_token(user_data)

        if not user_data:
            raise HTTPException(status_code=401, detail="No se pudo autenticar al usuario")

        return {
            "message": "Usuario autenticado exitosamente",
            "user": user_data,
            "token": token

        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")