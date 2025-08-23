
"""
Authentication middleware
"""
import jwt
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from config.settings import settings
from utils.helpers.logger import logger

class AuthMiddleware(BaseHTTPMiddleware):
    """JWT Authentication middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.secret_key = settings.app.secret_key
        self.algorithm = "HS256"
        
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with authentication"""
        path = request.url.path
        
        # Skip authentication for public endpoints
        if path in self.public_endpoints or path.startswith("/static"):
            return await call_next(request)
        
        # Extract and validate token
        token = self._extract_token(request)
        if not token:
            logger.log_structured('warning', 'Missing authentication token',
                                client_ip=request.client.host if request.client else "unknown",
                                endpoint=path)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        try:
            # Decode and validate JWT token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Add user info to request state
            request.state.user_id = user_id
            request.state.user_email = payload.get("email")
            request.state.user_role = payload.get("role", "user")
            
            # Log authenticated request
            logger.log_user_action(user_id, 'api_request', {
                'endpoint': path,
                'method': request.method
            })
            
        except jwt.ExpiredSignatureError:
            logger.log_structured('warning', 'Expired token used',
                                endpoint=path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            logger.log_structured('warning', 'Invalid token used',
                                endpoint=path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Process request
        response = await call_next(request)
        return response
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request"""
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Check query parameter (less secure, for development only)
        if settings.app.debug:
            return request.query_params.get("token")
        
        return None
