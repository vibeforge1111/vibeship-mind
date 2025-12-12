"""FastAPI server for Mind HTTP API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mind.api.errors import MindAPIError, mind_exception_handler
from mind.api import deps


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup: storage initialized lazily on first request
    yield
    # Shutdown: cleanup connections
    await deps.cleanup()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Mind API",
        description="HTTP API for Mind - context engine for AI-assisted development",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Localhost only, so permissive is fine
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(MindAPIError, mind_exception_handler)

    # Mount routers
    from mind.api.routes import projects, system
    app.include_router(projects.router)
    app.include_router(system.router)

    return app


# Create default app instance
app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8765):
    """Run the server with uvicorn."""
    import uvicorn
    uvicorn.run(
        "mind.api.server:app",
        host=host,
        port=port,
        reload=False,
    )
