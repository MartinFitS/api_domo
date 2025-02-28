from fastapi import APIRouter, HTTPException
from pymongo import MongoClient

client = MongoClient("mongodb+srv://msernaggc:DOMO2025@domo.1fxwg.mongodb.net/?tls=true&tlsAllowInvalidCertificates=true")
db = client["Domo"] 
devices_collection = db["devices"]

router = APIRouter()

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
