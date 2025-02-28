import cv2
import os
import numpy as np
import base64
from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb+srv://msernaggc:DOMO2025@domo.1fxwg.mongodb.net/?tls=true&tlsAllowInvalidCertificates=true")
db = client["Domo"] 
faces_collection = db["faces"]

def recibir_foto(photos, username): 
    model_path = os.path.join(os.getcwd(), 'modeloLBPHFace.xml')
    face_recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    if os.path.exists(model_path):
        face_recognizer.read(model_path)

    processed = False

    for index, photo in enumerate(photos):
        try:
            if not isinstance(photo, str):
                print(f"Error: Imagen en índice {index} no es una cadena base64 válida")
                continue

            missing_padding = len(photo) % 4
            if missing_padding:
                photo += '=' * (4 - missing_padding)

            image_data = base64.b64decode(photo)
            image_array = np.frombuffer(image_data, dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if img is None:
                print(f"Error: No se pudo decodificar la imagen en índice {index}")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                processed = True
                print(f"✅ Rostros detectados en imagen {index} de {username}")

                face_document = {
                    "username": username,
                    "image_base64": photo,  
                    "date_uploaded": datetime.utcnow(),
                    "faces_detected": len(faces)  
                }

                faces_collection.insert_one(face_document)
                print(f"✅ Imagen {index} guardada en MongoDB")

        except Exception as e:
            print(f"❌ Error procesando la imagen {index}: {e}")

    if processed:
        print("✅ OK - Imágenes procesadas y guardadas correctamente")
    else:
        print("🚨 No se detectaron rostros o hubo un error en las imágenes")