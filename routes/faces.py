from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
import numpy as np
import cv2
from typing import List
import jwt
import base64
from datetime import datetime, timedelta 
from bson import ObjectId
import os
from services.faces import recibir_foto, train_model_function,recognize_face
from dotenv import load_dotenv


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB = os.getenv("DB_NAME")
FACES_COLLECTION = os.getenv("COLLECTION_FACES")

client = MongoClient(MONGO_URI)
db = client[DB] 
faces_collection = db[FACES_COLLECTION]

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

def preprocess_image(image_base64):
    """
    Convierte la imagen base64 a una imagen OpenCV, detecta rostros y la convierte a escala de grises.
    Devuelve la imagen recortada y preprocesada en base64.
    """
    try:
        # Decodificar imagen base64
        image_data = base64.b64decode(image_base64)
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("No se pudo decodificar la imagen")

        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detectar rostro con Haarcascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            raise ValueError("No se detectaron rostros en la imagen")

        # Recortar el primer rostro detectado
        (x, y, w, h) = faces[0]
        face_gray = gray[y:y+h, x:x+w]

        # Codificar la imagen recortada en base64
        _, buffer = cv2.imencode('.jpg', face_gray)
        face_base64 = base64.b64encode(buffer).decode('utf-8')

        return face_base64
    except Exception as e:
        print(f"❌ Error procesando la imagen: {e}")
        return None

def create_jwt_token(user_data):
    user_id = str(user_data["_id"]) if "_id" in user_data else None
    safe_user_data = {k: v for k, v in user_data.items() if not isinstance(v, bytes)}

    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=1),  # ✅ Solucionado
        "iat": datetime.utcnow(),  # ✅ Solucionado
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
        img_proccesed = preprocess_image(request.img)
        user_data = recognize_face(img_proccesed)  
        print(f"✅ Predicción realizada: {user_data}")

        if not user_data:
            raise HTTPException(status_code=401, detail="No se pudo autenticar al usuario")

        token = create_jwt_token(user_data)

        if "username" not in user_data:
            raise HTTPException(status_code=400, detail="No se encontró username en los datos del usuario")

        try:
            face_document = {
                "username": user_data["username"],
                "image_base64": request.img,
                "date_uploaded": datetime.utcnow(),  # ✅ Solucionado
                "faces_detected": 1
            }
            result = faces_collection.insert_one(face_document)
            print(f"✅ Imagen autenticada guardada en MongoDB con ID: {result.inserted_id}")

        except Exception as e:
            print(f"❌ Error al guardar la imagen en MongoDB: {e}")
            raise HTTPException(status_code=500, detail="Error guardando la imagen en la base de datos")

        # Intentar entrenar el modelo
        try:
            train_model()
            print("✅ Modelo actualizado con nueva imagen")

        except Exception as e:
            print(f"❌ Error al entrenar el modelo: {e}")
            raise HTTPException(status_code=500, detail="Error entrenando el modelo con la nueva imagen")

        return {
            "message": "Usuario autenticado exitosamente",
            "user": user_data,
            "token": token
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Error inesperado en el login: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")