from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
import cv2
import os
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from mtcnn import MTCNN
import shutil
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

data_path = os.path.join(os.getcwd(), 'Data')
os.makedirs(data_path, exist_ok=True)

detector = MTCNN()

model_path = os.path.join(os.getcwd(), 'modeloLBPHFace.xml')

face_recognizer = cv2.face.LBPHFaceRecognizer_create()
if os.path.exists(model_path):
    face_recognizer.read(model_path)

def save_image(person_name: str, image_data: bytes, file_name: str):
    """ Guarda la imagen en la carpeta correspondiente y extrae el rostro. """
    person_path = os.path.join(data_path, person_name)
    os.makedirs(person_path, exist_ok=True)

    temp_path = os.path.join(person_path, file_name)
    with open(temp_path, "wb") as f:
        f.write(image_data)

    img = cv2.imread(temp_path)
    if img is None:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail="Formato de imagen inválido")

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detector.detect_faces(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    count = len(os.listdir(person_path))  
    for face in faces:
        x, y, w, h = face['box']
        face_img = img_gray[y:y + h, x:x + w]
        face_img = cv2.resize(face_img, (150, 150), interpolation=cv2.INTER_CUBIC)
        face_path = os.path.join(person_path, f'face_{count}.jpg')
        cv2.imwrite(face_path, face_img)
        count += 1

    os.remove(temp_path)  

@app.post("/register-face")
async def register_face(
    request: Request,
    person_name: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """ Recibe y almacena las imágenes para entrenamiento. """
    form_data = await request.form()
    print(f"📌 Form Data Recibido en FastAPI: {form_data}")
    print(f"📌 Nombre recibido: {person_name}")
    print(f"📌 Número de archivos recibidos: {len(files)}")

    if not files:
        raise HTTPException(status_code=400, detail="No se recibieron archivos.")

    for file in files:
        image_data = await file.read()
        save_image(person_name, image_data, file.filename)

    return {"message": f"Se registraron {len(files)} imágenes para {person_name}"}

@app.get("/test")
def test():
    """ Endpoint para verificar si el servidor está funcionando. """
    return "pong"

@app.post("/train-model")
def train_model():
    """ Entrena el modelo de reconocimiento facial con las imágenes almacenadas. """
    labels, faces_data = [], []
    label = 0
    people_list = os.listdir(data_path)
    
    for person_name in people_list:
        person_path = os.path.join(data_path, person_name)
        for file_name in os.listdir(person_path):
            img_path = os.path.join(person_path, file_name)
            img = cv2.imread(img_path, 0)
            if img is None:
                continue
            faces_data.append(img)
            labels.append(label)
        label += 1

    if not faces_data:
        raise HTTPException(status_code=400, detail="No faces found for training")

    face_recognizer.train(faces_data, np.array(labels))
    face_recognizer.write(model_path)

    return {"message": "Model trained successfully"}

@app.post("/recognize-face")
def recognize_face(file: UploadFile = File(...)):
    """ Identifica el rostro en una imagen usando el modelo entrenado. """
    if not os.path.exists(model_path):
        raise HTTPException(status_code=400, detail="Model not trained yet")

    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    img = cv2.imread(temp_path)
    os.remove(temp_path)

    if img is None:
        raise HTTPException(status_code=400, detail="Formato de imagen inválido")

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detector.detect_faces(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if not faces:
        return {"message": "No face detected"}

    x, y, w, h = faces[0]['box']
    face_img = img_gray[y:y + h, x:x + w]
    face_img = cv2.resize(face_img, (150, 150), interpolation=cv2.INTER_CUBIC)

    label, confidence = face_recognizer.predict(face_img)
    image_paths = os.listdir(data_path)

    name = image_paths[label] if confidence < 70 else "Unknown"

    return {"name": name, "confidence": confidence}
