"""
Supply Chain Clerk — FastAPI Application Entry Point
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import intake, websocket_routes, status
from app.services.neo4j_setup import init_neo4j_schema
from app.services.mqtt_client import mqtt_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle manager."""
    # ── Startup ─────────────────────────────────────────────────────────────
    await init_neo4j_schema()
    asyncio.create_task(mqtt_manager.start())
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    await mqtt_manager.stop()


app = FastAPI(
    title="Supply Chain Clerk API",
    version="1.0.0",
    description=(
        "Agentic pipeline: VLM document parsing → Neo4j graph inventory "
        "→ MQTT IoT bin lighting"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(intake.router, prefix="/intake", tags=["Intake"])
app.include_router(websocket_routes.router, tags=["WebSocket"])
app.include_router(status.router, prefix="/status", tags=["Status"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "supply-chain-clerk"}
