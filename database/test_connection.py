from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base

# Banco de teste separado
TEST_DATABASE_URL = "postgresql://huntly_user:huntly_pass@localhost:5432/huntly_test"

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def get_test_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_test_tables():
    Base.metadata.create_all(bind=test_engine)

def drop_test_tables():
    Base.metadata.drop_all(bind=test_engine)
