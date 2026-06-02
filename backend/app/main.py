import time
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import db_manager, setup_collections
from app.routers import resume, match, interview, analytics, outreach

# --- Setup Global Logging Stream ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("app.main")

# --- Lifespan Events (Asynchronous MongoDB Atlas initialization) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB Atlas asynchronously on startup
    await db_manager.connect_to_database()
    # Create collection indexes and verify vector search index
    await setup_collections()
    yield
    # Safely release db connections on shutdown
    await db_manager.close_database_connection()

# --- Initialize ASGI App ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="High-performance asynchronous predictive career intelligence platform.",
    version="2.4.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- Standard CORS Middleware targeting http://localhost:3000 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Custom Request-Response Profiler Logging Middleware ---
@app.middleware("http")
async def profile_request_telemetry(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # Process route request
    response: Response = await call_next(request)

    process_duration_ms = (time.time() - start_time) * 1000
    logger.info(
        f"Client IP: {client_ip} | Method: {request.method} | "
        f"Route: {request.url.path} | Status: {response.status_code} | "
        f"Time: {process_duration_ms:.2f}ms"
    )
    # Expose custom timing headers in response details
    response.headers["X-Process-Time-Ms"] = f"{process_duration_ms:.2f}"
    return response

# --- Global Unhandled Exception Protection Middleware ---
@app.middleware("http")
async def catch_global_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error(f"Global server execution crash occurred on {request.url.path}: {exc}")
        # Print actual console traceback stack safely
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server execution error. Telemetry protection active."}
        )

# --- Route inclusions under /api/v1 prefix ---
app.include_router(resume.router, prefix=settings.API_V1_STR)
app.include_router(match.router, prefix=settings.API_V1_STR)
app.include_router(interview.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(outreach.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["health"])
async def check_api_health():
    """Simple status check endpoint."""
    return {
        "status": "healthy",
        "api_telemetry": "nominal",
        "version": "2.4.0",
        "database_connected": db_manager.db is not None
    }
