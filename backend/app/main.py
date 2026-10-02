from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import settings

app = FastAPI(title="Registro de horas", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todas las rutas cuelgan de /api (así el proxy de Vite y el despliegue usan un único prefijo).
api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)

app.include_router(api_router)
