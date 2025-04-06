from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from pymongo import MongoClient
import os
from dotenv import load_dotenv


class DeviceUpdateRequest(BaseModel):
    name: str
    settings: dict



MONGO_URI = os.getenv("MONGO_URI")
DB = os.getenv("DB_NAME")
COLLECTION_DEVICES = os.getenv("COLLECTION_DEVICES")
COLLECTION_USERS = os.getenv("COLLECTION_USERS")  # Colección de usuarios



client = MongoClient(MONGO_URI)
db = client[DB] 
users_collection = db[COLLECTION_USERS]  

devices_collection = db[COLLECTION_DEVICES]

router = APIRouter()
class UserRequest(BaseModel):
    username: str


@router.get("/get_catalogue/devices")
def catalogue_devices():
    try:
        # Obtener todos los dispositivos de la colección 'devices'
        devices = list(devices_collection.find({}))  # find({}) obtiene todos los documentos

        # Si no hay dispositivos en la colección
        if not devices:
            raise HTTPException(status_code=404, detail="No devices found in the catalogue")

        # Eliminar el campo _id para evitar que sea enviado en la respuesta
        for device in devices:
            device.pop("_id", None)

        return {"devices": devices}  # Retornar la lista de dispositivos

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving devices: {str(e)}")
    

@router.post("/get_devices")
def get_devices(user: UserRequest):
    try:
        # Buscar al usuario en la colección 'users' por su username
        user_data = users_collection.find_one({"username": user.username})

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        # Obtener la lista de dispositivos del usuario
        devices = user_data.get("devices", [])

        if not devices:
            raise HTTPException(status_code=404, detail="No devices found for this user")
        
        print(devices)

        return {"devices": devices}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user devices: {str(e)}")
    

@router.put("/{device_id}/{username}")
def update_user_device(device_id: str, username: str, update: DeviceUpdateRequest = Body(...)):
    try:
        # Buscar al usuario
        user = users_collection.find_one({"username": username})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        devices = user.get("devices", {})

        device_found = False

        for key, device in devices.items():
            if device.get("id") == device_id:
                for k, v in update.settings.items():
                    device[k] = v  # sobrescribe directamente
                device["name"] = update.name
                device_found = True
                break

        if not device_found:
            raise HTTPException(status_code=404, detail="Device not found for user")

        # Actualizar el documento en la base de datos
        users_collection.update_one(
            {"username": username},
            {"$set": {"devices": devices}}
        )

        return {"message": "Device updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating device: {str(e)}")