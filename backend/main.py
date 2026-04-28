from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.shipments import router as shipments_router
from routes.routing_api import router as routing_router
from routes.phase4_api import router as phase4_router
from routes.phase5_api import router as phase5_router
from ws.routes import ws_router
from ws.manager import manager
from simulation.engine import simulation_loop, set_ws_manager

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Smart Supply Chain API",
    description="Phase 5 — Self-Healing + Control Tower + Analytics",
    version="5.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://routesense-five.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shipments_router)
app.include_router(routing_router)
app.include_router(phase4_router)
app.include_router(phase5_router)
app.include_router(ws_router)


@app.on_event("startup")
async def startup():
    set_ws_manager(manager)
    asyncio.create_task(simulation_loop())


@app.get("/")
def root():
    return {"message": "Smart Supply Chain API v5 running", "docs": "/docs", "phase": 5}

@app.get("/health")
def health():
    return {"status": "ok", "version": "5.0.0"}
