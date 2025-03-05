import cv2
import os
import numpy as np
import base64
from pymongo import MongoClient
from datetime import datetime
from fastapi import HTTPException
from dotenv import load_dotenv


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB = os.getenv("DB_NAME")
FACES_COLLECTION = os.getenv("COLLECTION_FACES")


client = MongoClient(MONGO_URI)
db = client[DB] 
faces_collection = db[FACES_COLLECTION]

model_path = os.path.join(os.getcwd(), 'modeloLBPHFace.xml')
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

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

                # Recortar la cara detectada
                for (x, y, w, h) in faces:
                    face = img[y:y+h, x:x+w]  # Recorta la cara de la imagen
                    face_gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)  # Convertir a escala de grises

                    # Codificar la imagen recortada en base64
                    _, buffer = cv2.imencode('.jpg', face_gray)
                    face_base64 = base64.b64encode(buffer).decode('utf-8')

                    # Guardar la imagen recortada en la base de datos
                    face_document = {
                        "username": username,
                        "image_base64": face_base64,
                        "date_uploaded": datetime.utcnow(),
                        "faces_detected": len(faces)  
                    }

                    faces_collection.insert_one(face_document)
                    print(f"✅ Imagen {index} recortada y guardada en MongoDB")

        except Exception as e:
            print(f"❌ Error procesando la imagen {index}: {e}")

    if processed:
        print("✅ OK - Imágenes procesadas y guardadas correctamente")
    else:
        print("🚨 No se detectaron rostros o hubo un error en las imágenes")
        
def train_model_function():
    """Entrena el modelo de reconocimiento facial con las imágenes almacenadas en MongoDB y asigna labels a los usuarios."""
    
    labels, faces_data = [], []
    label_mapping = {}  # Diccionario para mapear username a label
    label_counter = 0   # Contador de etiquetas únicas

    face_documents = faces_collection.find()

    for face_doc in face_documents:
        username = face_doc["username"]
        img_base64 = face_doc["image_base64"]

        # Decodificar la imagen base64
        image_data = base64.b64decode(img_base64)
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)

        if img is None:
            continue

        if username not in label_mapping:
            label_mapping[username] = label_counter
            label_counter += 1

        labels.append(label_mapping[username])
        faces_data.append(img)

    if not faces_data:
        raise HTTPException(status_code=400, detail="No hay suficientes rostros para entrenar el modelo")

    model_path = os.path.join(os.getcwd(), 'modeloLBPHFace.xml')
    face_recognizer = cv2.face.LBPHFaceRecognizer_create()
    face_recognizer.train(faces_data, np.array(labels))
    face_recognizer.write(model_path)  

    for username, label in label_mapping.items():
        db["users"].update_one(
            {"username": username},
            {"$set": {"label": label}}
        )

    print("✅ Modelo entrenado exitosamente y labels asignados a los usuarios")


def recognize_face(photo_base64):
    model_path = os.path.join(os.getcwd(), 'modeloLBPHFace.xml')
    
    if not os.path.exists(model_path):
        print("❌ ERROR: Modelo de reconocimiento no encontrado.")
        raise HTTPException(status_code=500, detail="Modelo de reconocimiento no encontrado. Entrena el modelo primero.")

    face_recognizer = cv2.face.LBPHFaceRecognizer_create()
    face_recognizer.read(model_path)

    try:
        image_data = base64.b64decode(photo_base64)
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if img is None:
            print("❌ ERROR: No se pudo decodificar la imagen base64.")
            raise HTTPException(status_code=400, detail="No se pudo decodificar la imagen")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            print("❌ ERROR: No se detectaron rostros en la imagen.")
            raise HTTPException(status_code=400, detail="No se detectaron rostros en la imagen")

        x, y, w, h = faces[0]
        face_crop = gray[y:y+h, x:x+w]

        label, confidence = face_recognizer.predict(face_crop)

        print(f"✅ Predicción realizada: Label={label}, Confianza={confidence}")

        CONFIDENCE_THRESHOLD = 70  

        if confidence > CONFIDENCE_THRESHOLD:
            print(f"❌ Confianza demasiado alta ({confidence}), usuario no reconocido.")
            raise HTTPException(status_code=401, detail="Usuario no reconocido. Intente de nuevo.")


        user_document = db["users"].find_one({"label": label})

        if not user_document:
            print("❌ ERROR: Usuario no encontrado en la base de datos.")
            raise HTTPException(status_code=404, detail="Usuario no encontrado en la base de datos")
        
        print(user_document)

        return {
            "username": user_document.get("username"),
            "devices": user_document.get("devices"),
            "nombre": user_document.get("name"),
            "label": label,
            "confidence": confidence
        }

    except Exception as e:
        print(f"❌ ERROR INTERNO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en el reconocimiento facial: {str(e)}")
