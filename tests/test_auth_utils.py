import pytest
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables before importing
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "sqlite:///test.db"

from auth.utils import (
    get_password_hash, verify_password, create_access_token, 
    verify_token, validate_password_strength
)

class TestPasswordUtils:
    """Test password hashing and verification utilities"""
    
    def test_password_hashing(self):
        """Test password hashing works correctly"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_password_validation(self):
        """Test password strength validation"""
        assert validate_password_strength("12345678") is True
        assert validate_password_strength("short") is False
        assert validate_password_strength("") is False
    
    def test_invalid_password_hashing(self):
        """Test error handling for invalid passwords"""
        with pytest.raises(ValueError):
            get_password_hash("")
        
        with pytest.raises(ValueError):
            get_password_hash("ab")

class TestJWTTokens:
    """Test JWT token creation and verification"""
    
    def test_access_token_creation(self):
        """Test access token creation and verification"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token
        payload = verify_token(token, "access")
        assert payload["sub"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_invalid_token_verification(self):
        """Test invalid token handling"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException):
            verify_token("invalid_token", "access")
        
        with pytest.raises(HTTPException):
            verify_token("", "access")

if __name__ == "__main__":
    pytest.main([__file__])