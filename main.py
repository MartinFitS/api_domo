from fastapi import FastAPI
from routes.faces import router as faces_router
from routes.devices import router as device_router
from fastapi.middleware.cors import CORSMiddleware
from routes.users import router as users_router

app = FastAPI(title="DOMO API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(faces_router, prefix="/api/faces")
app.include_router(device_router, prefix="/api/devices")
app.include_router(users_router, prefix="/api/users")
