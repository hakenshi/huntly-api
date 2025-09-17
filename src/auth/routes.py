from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..models.auth import UserCreate, UserLogin, Token, User
from ..database.models import User as DBUser
from ..database.connection import get_db
from .utils import (
    verify_password, get_password_hash, validate_password_strength,
    create_access_token, create_refresh_token, verify_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import logging

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with enhanced security"""
    try:
        # Verificar se email já existe
        existing_user = db.query(DBUser).filter(DBUser.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="Email já está registrado"
            )
        
        # Validar força da senha
        if not validate_password_strength(user.password):
            raise HTTPException(
                status_code=400,
                detail="Senha deve ter pelo menos 8 caracteres"
            )
        
        # Criar usuário
        db_user = DBUser(
            email=user.email,
            name=user.name,
            password_hash=get_password_hash(user.password)
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Criar tokens
        access_token = create_access_token(data={"sub": user.email})
        
        logging.info(f"New user registered: {user.email}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token with enhanced security"""
    try:
        # Buscar usuário
        db_user = db.query(DBUser).filter(DBUser.email == user.email).first()
        
        if not db_user or not verify_password(user.password, db_user.password_hash):
            # Log failed login attempt
            logging.warning(f"Failed login attempt for email: {user.email}")
            raise HTTPException(
                status_code=401, 
                detail="Email ou senha inválidos"
            )
        
        # Criar tokens
        access_token = create_access_token(data={"sub": user.email})
        
        logging.info(f"User logged in: {user.email}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/me", response_model=User)
def get_me(current_user: DBUser = Depends(get_current_user)):
    """Get current user information"""
    return {
        "email": current_user.email,
        "name": current_user.name
    }

@router.post("/refresh", response_model=Token)
def refresh_access_token(current_user: DBUser = Depends(get_current_user)):
    """Refresh access token for authenticated user"""
    try:
        access_token = create_access_token(data={"sub": current_user.email})
        
        logging.info(f"Token refreshed for user: {current_user.email}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except Exception as e:
        logging.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao renovar token")