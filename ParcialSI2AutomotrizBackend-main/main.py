from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router
from routes.vehiculos import router as vehiculos_router
from routes.talleres import router as talleres_router
from routes.bitacora import router as bitacora_router
from routes.emergencias import router as emergencias_router
from routes.notificaciones import router as notificaciones_router

app = FastAPI(
    title="ResQ Auto API",
    description="API de Plataforma Inteligente de Atención de Emergencias Vehiculares",
    version="2.0.0"
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth_router)
app.include_router(vehiculos_router)
app.include_router(talleres_router)
app.include_router(bitacora_router)
app.include_router(emergencias_router)
app.include_router(notificaciones_router)


@app.get("/")
def root():
    return {"mensaje": "ResQ Auto API - v2.0.0", "estado": "activo"}