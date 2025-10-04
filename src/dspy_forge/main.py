import os
import argparse

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from dspy_forge.core.config import settings
from dspy_forge.core.logging import setup_logging, get_logger
from dspy_forge.api.routes import router as api_router

# Set Databricks SDK environment variables from settings
if settings.databricks_config_profile:
    os.environ["MLFLOW_ENABLE_DB_SDK"]  = "true"
    os.environ["DATABRICKS_CONFIG_PROFILE"] = settings.databricks_config_profile
elif settings.databricks_host and settings.databricks_token:
    os.environ["MLFLOW_ENABLE_DB_SDK"]  = "true"
    os.environ["DATABRICKS_HOST"] = settings.databricks_host
    os.environ["DATABRICKS_TOKEN"] = settings.databricks_token
else:
    raise ValueError("Databricks configuration not provided in environment variables.")

# Initialize logging
setup_logging(
    level=settings.log_level,
    log_file=settings.log_file
)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.0.1",
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix=settings.api_prefix)

    # Serve React static files
    static_dir = Path(__file__).parent.parent.parent / "ui/build"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir / "static")), name="static")

    # Serve React app for all other routes
    @app.get("/")
    async def serve_react_app():
        """Serve React app for all routes not handled by API"""
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/dspy.png")
    async def serve_dspy_image():
        """Serve the dspy.png image"""
        return FileResponse(str(static_dir / "dspy.png"))

    return app


app = create_app()


def parse_server_args():
    """Parse command line arguments for the agent server"""
    parser = argparse.ArgumentParser(description="Start the agent server")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Number of workers to run the server on (default: 1)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload the server on code changes (default: False)",
    )
    return parser.parse_args()


def run():
    """Entry point for the dspy-forge command"""
    import uvicorn

    args = parse_server_args()

    uvicorn.run(
        "dspy_forge.main:app",
        host="0.0.0.0",
        port=args.port,
        workers=args.workers,
        reload=args.reload,
    )

if __name__ == "__main__":
    run()