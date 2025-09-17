from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter pelo menos 8 caracteres')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Nome deve ter pelo menos 2 caracteres')
        return v.strip()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = None

class TokenData(BaseModel):
    email: Optional[str] = None

class User(BaseModel):
    email: str
    name: str
    plan_type: Optional[str] = "starter"
    
    model_config = {"from_attributes": True}