"""
ULTRON - Autonomous AI Procurement and Payment Agent
Main FastAPI Application Entry Point (backend/main.py)
"""
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from backend.config import BASE_DIR, settings
from backend.database import db_manager
from backend.integrations.openrouter import openrouter_client
from backend.integrations.paypal import paypal_client
from backend.routes import agents, orders, payments, procurement, products

app = FastAPI(
    title="ULTRON — Autonomous AI Procurement and Payment Agent",
    description=(
        "Production-grade autonomous AI procurement platform with Multi-Agent Orchestration, "
        "MySQL 8+ persistence, OpenRouter/Groq AI reasoning, Channel3 Product Discovery, "
        "and PayPal Sandbox REST v2 checkout & capture."
    ),
    version="4.8.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Modular API Routers
app.include_router(procurement.router)
app.include_router(products.router)
app.include_router(agents.router)
app.include_router(orders.router)
app.include_router(payments.router)


@app.get("/api/health", tags=["System Health"])
async def system_health():
    ai_status = openrouter_client.get_status()
    pp_status = await paypal_client.verify_merchant_identity(force_refresh=False)
    return {
        "status": "OPERATIONAL",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "database": {
            "engine": "MySQL 8.0+ / Resilient Sync",
            "mysql_connected": db_manager.mysql_connected,
            "status": db_manager.mysql_status_message,
        },
        "integrations": {
            "active_ai_provider": ai_status,
            "openrouter_configured": settings.is_openrouter_configured,
            "groq_configured": settings.is_groq_configured,
            "paypal_sandbox": pp_status,
            "channel3_configured": settings.is_channel3_configured,
        },
    }


@app.get("/ULTRON_GITHUB_READY.zip", tags=["Export"])
@app.get("/api/export/github-zip", tags=["Export"])
async def download_github_zip():
    zip_path = BASE_DIR / "ULTRON_GITHUB_READY.zip"
    if not zip_path.exists():
        # Generate on the fly if missing
        from build_zip import create_github_ready_zip

        create_github_ready_zip()
    if zip_path.exists():
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename="ULTRON_GITHUB_READY.zip",
        )
    return JSONResponse(status_code=404, content={"error": "ULTRON_GITHUB_READY.zip not found"})


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    index_file: Path = BASE_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(
            content="<h1>ULTRON index.html not found</h1>",
            status_code=404,
        )
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )
