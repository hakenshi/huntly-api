from sqlalchemy.orm import Session
from .connection import SessionLocal, engine
from .models import Base, User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_users():
    # Criar tabelas
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    # Verificar se já existem usuários
    if db.query(User).first():
        print("Usuários já existem no banco")
        db.close()
        return
    
    # Usuários de teste
    test_users = [
        {
            "email": "admin@huntly.com",
            "name": "Admin Huntly",
            "plan_type": "enterprise"
        },
        {
            "email": "joao@empresa.com", 
            "name": "João Silva",
            "plan_type": "professional"
        },
        {
            "email": "maria@startup.com",
            "name": "Maria Santos", 
            "plan_type": "starter"
        },
        {
            "email": "teste@teste.com",
            "name": "Usuário Teste",
            "plan_type": "starter"
        }
    ]
    
    # Criar usuários
    for user_data in test_users:
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            password_hash=get_password_hash("123"),
            plan_type=user_data["plan_type"]
        )
        db.add(user)
    
    db.commit()
    db.close()
    
    print("✅ Usuários criados com sucesso!")
    print("Senha para todos: 123")
    for user in test_users:
        print(f"- {user['email']} ({user['plan_type']})")

if __name__ == "__main__":
    seed_users()