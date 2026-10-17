from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.telemetry import router as telemetry_router
from storage.database import initialize_database
from storage import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize / upgrade schema once at application startup
    initialize_database()
    yield


app = FastAPI(
    title="Project Apex-01 Telemetry Backend",
    description="Real-time motorsport telemetry receiving, processing, analytics, alerts and storage backend.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local dashboards and network devices (e.g. ESP32, web dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry_router)


@app.get("/")
def root():
    return {"project": "Apex-01", "status": "online", "service": "Telemetry Backend", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "apex01-backend"}
