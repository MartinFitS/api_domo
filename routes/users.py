from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
import bcrypt
import jwt
from datetime import datetime, timedelta

client = MongoClient("mongodb+srv://msernaggc:DOMO2025@domo.1fxwg.mongodb.net/?tls=true&tlsAllowInvalidCertificates=true")
db = client["Domo"]
users_collection = db["users"]
licenses_collection = db["licencias"]

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    name: str
    apellido: str
    contrasena: str
    licencia: str
    deviceSettings: dict

SECRET_KEY = "tu_clave_secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/create-user")
def create_user(user: UserCreate):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    license_data = licenses_collection.find_one({"auth_hash": user.licencia})

    if not license_data:
        raise HTTPException(status_code=400, detail="La licencia no existe")

    if license_data.get("is_active", False):
        raise HTTPException(status_code=400, detail="La licencia ya está activada")

    hashed_password = bcrypt.hashpw(user.contrasena.encode('utf-8'), bcrypt.gensalt())

    new_user = {
        "username": user.username,
        "name": user.name,
        "apellido": user.apellido,
        "contrasena": hashed_password,
        "licencia": user.licencia,
        "devices": user.deviceSettings
    }

    users_collection.insert_one(new_user)

    licenses_collection.update_one(
        {"auth_hash": user.licencia},
        {"$set": {"is_active": True}}
    )

    access_token = create_access_token(data={"sub": user.username})

    return {"message": "Usuario creado exitosamente", "access_token": access_token}


