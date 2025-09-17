"""
Unit tests for scraping utilities
"""

import pytest
from src.scraping.utils import (
    clean_text, extract_email, extract_phone_br, validate_url,
    normalize_company_name, calculate_text_similarity, is_business_email,
    extract_location_br, get_domain_from_url, is_valid_company_website,
    format_scraped_data, calculate_data_quality_score
)

class TestTextCleaning:
    """Test text cleaning utilities"""
    
    def test_clean_text(self):
        """Test text cleaning function"""
        assert clean_text("  Hello   World  ") == "hello world"
        assert clean_text("Company@#$%Name") == "company name"
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_normalize_company_name(self):
        """Test company name normalization"""
        assert normalize_company_name("TechCorp LTDA.") == "techcorp"
        assert normalize_company_name("Software Inc") == "software"
        assert normalize_company_name("Empresa SA") == "empresa"

class TestEmailExtraction:
    """Test email extraction utilities"""
    
    def test_extract_email(self):
        """Test email extraction from text"""
        text = "Contact us at info@company.com or sales@business.org"
        assert extract_email(text) == "info@company.com"
        
        # Should skip noreply emails
        text = "Email: noreply@company.com"
        assert extract_email(text) is None
        
        # Should handle no email
        assert extract_email("No email here") is None
    
    def test_is_business_email(self):
        """Test business email detection"""
        assert is_business_email("contact@company.com") is True
        assert is_business_email("user@gmail.com") is False
        assert is_business_email("info@business.com.br") is True
        assert is_business_email("test@yahoo.com") is False

class TestPhoneExtraction:
    """Test phone number extraction"""
    
    def test_extract_phone_br(self):
        """Test Brazilian phone extraction"""
        assert extract_phone_br("(11) 99999-9999") == "(11) 99999-9999"
        assert extract_phone_br("11 98888-8888") == "11 98888-8888"
        assert extract_phone_br("+55 21 97777-7777") == "+55 21 97777-7777"
        assert extract_phone_br("No phone here") is None

class TestLocationExtraction:
    """Test location extraction"""
    
    def test_extract_location_br(self):
        """Test Brazilian location extraction"""
        assert extract_location_br("São Paulo, SP") == "São Paulo, SP"
        assert extract_location_br("Rio de Janeiro") == "Rio de Janeiro"
        assert extract_location_br("Endereço em SP") == "SP"
        assert extract_location_br("No location") is None

class TestURLValidation:
    """Test URL validation utilities"""
    
    def test_validate_url(self):
        """Test URL validation"""
        assert validate_url("https://company.com") is True
        assert validate_url("http://business.com.br") is True
        assert validate_url("invalid-url") is False
        assert validate_url("") is False
    
    def test_get_domain_from_url(self):
        """Test domain extraction from URL"""
        assert get_domain_from_url("https://company.com/page") == "company.com"
        assert get_domain_from_url("http://sub.business.com.br") == "sub.business.com.br"
        assert get_domain_from_url("invalid") is None
    
    def test_is_valid_company_website(self):
        """Test company website validation"""
        assert is_valid_company_website("https://company.com") is True
        assert is_valid_company_website("https://google.com") is False
        assert is_valid_company_website("https://facebook.com") is False
        assert is_valid_company_website("invalid-url") is False

class TestTextSimilarity:
    """Test text similarity calculation"""
    
    def test_calculate_text_similarity(self):
        """Test text similarity calculation"""
        assert calculate_text_similarity("TechCorp", "TechCorp") == 1.0
        assert calculate_text_similarity("Tech Corp", "TechCorp LTDA") > 0.5
        assert calculate_text_similarity("Apple", "Microsoft") == 0.0
        assert calculate_text_similarity("", "anything") == 0.0

class TestDataFormatting:
    """Test data formatting utilities"""
    
    def test_format_scraped_data(self):
        """Test scraped data formatting"""
        raw_data = {
            "company": "  TECH CORP LTDA  ",
            "email": "CONTACT@COMPANY.COM",
            "phone": "(11) 99999-9999",
            "website": "https://company.com",
            "description": "  Software development company  "
        }
        
        formatted = format_scraped_data(raw_data)
        
        assert formatted["company"] == "tech corp ltda"
        assert formatted["email"] == "contact@company.com"
        assert formatted["phone"] == "(11) 99999-9999"
        assert formatted["website"] == "https://company.com"
        assert formatted["description"] == "software development company"
        assert "scraped_at" in formatted
        assert "data_quality_score" in formatted
    
    def test_calculate_data_quality_score(self):
        """Test data quality score calculation"""
        # High quality data
        high_quality = {
            "company": "TechCorp",
            "email": "contact@techcorp.com",
            "phone": "(11) 99999-9999",
            "website": "https://techcorp.com",
            "industry": "Technology",
            "location": "São Paulo",
            "description": "Software company"
        }
        
        score = calculate_data_quality_score(high_quality)
        assert score > 0.8
        
        # Low quality data
        low_quality = {"company": "Company"}
        score = calculate_data_quality_score(low_quality)
        assert score <= 0.3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])