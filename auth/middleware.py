from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User
from .utils import verify_token
import logging
from typing import Optional

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for protected routes"""
    
    def __init__(self, app, protected_paths: list = None):
        super().__init__(app)
        self.protected_paths = protected_paths or [
            "/leads",
            "/campaigns", 
            "/analytics",
            "/auth/me",
            "/auth/refresh"
        ]
        self.security = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        # Check if path requires authentication
        path = request.url.path
        requires_auth = any(path.startswith(protected) for protected in self.protected_paths)
        
        if requires_auth:
            # Extract token from Authorization header
            authorization = request.headers.get("Authorization")
            
            if not authorization or not authorization.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            token = authorization.split(" ")[1]
            
            try:
                # Verify token
                payload = verify_token(token, "access")
                
                # Add user info to request state
                request.state.user_email = payload.get("sub")
                request.state.token_payload = payload
                
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
            except Exception as e:
                logging.error(f"Authentication middleware error: {e}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication failed"}
                )
        
        response = await call_next(request)
        return response

def require_auth(required_scopes: list = None):
    """Decorator for route-level authentication requirements"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be used with dependency injection
            # Implementation depends on specific FastAPI setup
            return await func(*args, **kwargs)
        return wrapper
    return decorator