from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import UserCreate, UserLogin, Token, User
from database.models import User as DBUser
from database.connection import get_db
from auth.utils import (
    verify_password, get_password_hash,
    create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar se email já existe
    if db.query(DBUser).filter(DBUser.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Criar usuário
    db_user = DBUser(
        email=user.email,
        name=user.name,
        password_hash=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Buscar usuário
    db_user = db.query(DBUser).filter(DBUser.email == user.email).first()
    
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
def get_me(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.email == current_user).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "email": db_user.email,
        "name": db_user.name
    }
