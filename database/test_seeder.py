from sqlalchemy.orm import Session
from database.test_connection import TestSessionLocal, test_engine, create_test_tables
from database.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_test_users():
    # Criar tabelas de teste
    create_test_tables()
    
    db: Session = TestSessionLocal()
    
    # Limpar usuários existentes
    db.query(User).delete()
    
    # Usuários de teste
    test_users = [
        {
            "email": "test1@test.com",
            "name": "Test User 1",
            "plan_type": "starter"
        },
        {
            "email": "test2@test.com", 
            "name": "Test User 2",
            "plan_type": "professional"
        },
        {
            "email": "admin@test.com",
            "name": "Admin Test",
            "plan_type": "enterprise"
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
    
    print("✅ Usuários de teste criados!")
    print("Senha para todos: 123")
    for user in test_users:
        print(f"- {user['email']} ({user['plan_type']})")

if __name__ == "__main__":
    seed_test_users()
