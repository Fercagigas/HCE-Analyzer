
"""
FastAPI main application
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
from config.settings import settings
from utils.helpers.logger import logger
from api.middleware.rate_limiter import RateLimitMiddleware
from api.middleware.auth_middleware import AuthMiddleware
from api.routes import analysis, reports, alerts, backup, dashboard

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.log_structured('info', 'HCE Analyzer Pro API starting up')
    yield
    # Shutdown
    logger.log_structured('info', 'HCE Analyzer Pro API shutting down')

# Create FastAPI app
app = FastAPI(
    title="HCE Analyzer Pro API",
    description="Advanced Medical Records Analysis System",
    version="2.0.0",
    docs_url="/docs" if settings.app.debug else None,
    redoc_url="/redoc" if settings.app.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.app.debug else ["yourdomain.com", "*.yourdomain.com"]
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(backup.router, prefix="/api/v1/backup", tags=["Backup"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HCE Analyzer Pro API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs" if settings.app.debug else "Contact administrator"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": logger.logger.handlers[0].formatter.formatTime(
            logger.logger.makeRecord("", 0, "", 0, "", (), None)
        ),
        "version": "2.0.0"
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    logger.log_structured('warning', 'HTTP exception occurred',
                        status_code=exc.status_code,
                        detail=exc.detail,
                        path=str(request.url))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.log_error_with_context(exc, {
        'path': str(request.url),
        'method': request.method
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower()
    )
