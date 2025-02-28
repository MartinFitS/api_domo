from pymongo import MongoClient

MONGO_URI = "mongodb+srv://msernaggc:DOMO2025@domo.1fxwg.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client["Domo"]
devices_collection = db["devices"]

# Definir los dispositivos disponibles
default_devices = [
    {"device_id": "0", "device_type": 0, "name": "LED", "default_preferences": {"brightness": "50%", "mode": "normal"}},
    {"device_id": "1", "device_type": 1, "name": "Ventilador", "default_preferences": {"speed": "medium", "oscillate": "on"}},
    {"device_id": "2", "device_type": 2, "name": "Aire Acondicionado", "default_preferences": {"temperature": "24°C", "mode": "cool"}},
    {"device_id": "3", "device_type": 3, "name": "Bocina", "default_preferences": {"volume": "50%", "equalizer": "flat"}}
]

# Insertar los dispositivos en la base de datos (evitar duplicados)
for device in default_devices:
    if not devices_collection.find_one({"device_id": device["device_id"]}):
        devices_collection.insert_one(device)

print("📌 Dispositivos inicializados en MongoDB")
