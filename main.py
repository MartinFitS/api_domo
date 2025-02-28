from fastapi import FastAPI
from routes.faces import router as faces_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DOMO API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(faces_router, prefix="/api/faces")
