"""
Utility functions for scraping system
"""
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Convert to lowercase and strip
    text = text.lower().strip()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-\.\,\(\)]', ' ', text)
    
    return text.strip()

def extract_email(text: str) -> Optional[str]:
    """Extract email from text using regex"""
    if not text:
        return None
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    if matches:
        # Filter out common non-business emails
        skip_patterns = ['noreply', 'no-reply', 'example', 'test', 'admin', 'info@example']
        for email in matches:
            email_lower = email.lower()
            if not any(skip in email_lower for skip in skip_patterns):
                return email_lower
    
    return None

def extract_phone_br(text: str) -> Optional[str]:
    """Extract Brazilian phone number from text"""
    if not text:
        return None
    
    # Brazilian phone patterns
    patterns = [
        r'\(\d{2}\)\s*\d{4,5}-?\d{4}',  # (11) 99999-9999
        r'\d{2}\s*\d{4,5}-?\d{4}',      # 11 99999-9999
        r'\+55\s*\d{2}\s*\d{4,5}-?\d{4}', # +55 11 99999-9999
        r'\d{4,5}-?\d{4}',              # 99999-9999
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Return the first match, cleaned up
            phone = matches[0]
            # Remove extra spaces and format consistently
            phone = re.sub(r'\s+', ' ', phone)
            return phone
    
    return None

def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def normalize_company_name(name: str) -> str:
    """Normalize company name for comparison"""
    if not name:
        return ""
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove common business suffixes
    suffixes = ['ltda', 'ltd', 'inc', 'corp', 'sa', 'me', 'eireli', 'epp']
    for suffix in suffixes:
        name = re.sub(rf'\b{suffix}\.?\b', '', name)
    
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity score"""
    if not text1 or not text2:
        return 0.0
    
    # Normalize texts
    text1 = normalize_company_name(text1)
    text2 = normalize_company_name(text2)
    
    # Simple word overlap calculation
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

def is_business_email(email: str) -> bool:
    """Check if email looks like a business email"""
    if not email:
        return False
    
    # Skip common personal email providers
    personal_domains = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'uol.com.br', 'terra.com.br', 'bol.com.br', 'ig.com.br'
    ]
    
    domain = email.split('@')[-1].lower()
    return domain not in personal_domains

def extract_location_br(text: str) -> Optional[str]:
    """Extract Brazilian location from text"""
    if not text:
        return None
    
    # Brazilian states abbreviations
    states = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    
    # Common Brazilian cities
    cities = [
        'São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Brasília',
        'Salvador', 'Fortaleza', 'Curitiba', 'Recife', 'Porto Alegre',
        'Manaus', 'Belém', 'Goiânia', 'Guarulhos', 'Campinas'
    ]
    
    text_upper = text.upper()
    
    # Look for city, state pattern
    for city in cities:
        if city.upper() in text_upper:
            # Try to find state after city
            for state in states:
                pattern = rf'{re.escape(city.upper())}[,\s]*{state}'
                if re.search(pattern, text_upper):
                    return f"{city}, {state}"
            return city
    
    # Look for just state
    for state in states:
        if f' {state}' in text_upper or f',{state}' in text_upper:
            return state
    
    return None

def get_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except:
        return None

def is_valid_company_website(url: str) -> bool:
    """Check if URL looks like a valid company website"""
    if not validate_url(url):
        return False
    
    domain = get_domain_from_url(url)
    if not domain:
        return False
    
    # Skip common non-company domains
    skip_domains = [
        'google.com', 'facebook.com', 'linkedin.com', 'twitter.com',
        'instagram.com', 'youtube.com', 'wikipedia.org', 'amazon.com',
        'mercadolivre.com.br', 'olx.com.br', 'reclameaqui.com.br',
        'guiamais.com.br', 'paginas-amarelas.com'
    ]
    
    return not any(skip_domain in domain for skip_domain in skip_domains)

def format_scraped_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format and clean scraped data"""
    formatted = {}
    
    # Clean text fields
    text_fields = ['company', 'contact', 'description', 'industry', 'location', 'address']
    for field in text_fields:
        if field in raw_data and raw_data[field]:
            formatted[field] = clean_text(str(raw_data[field]))
    
    # Clean and validate email
    if 'email' in raw_data and raw_data['email']:
        email = extract_email(str(raw_data['email']))
        if email and is_business_email(email):
            formatted['email'] = email
    
    # Clean and validate phone
    if 'phone' in raw_data and raw_data['phone']:
        phone = extract_phone_br(str(raw_data['phone']))
        if phone:
            formatted['phone'] = phone
    
    # Validate website URL
    if 'website' in raw_data and raw_data['website']:
        url = str(raw_data['website'])
        if is_valid_company_website(url):
            formatted['website'] = url
    
    # Add metadata
    formatted['scraped_at'] = datetime.now(timezone.utc).isoformat()
    formatted['data_quality_score'] = calculate_data_quality_score(formatted)
    
    return formatted

def calculate_data_quality_score(data: Dict[str, Any]) -> float:
    """Calculate data quality score (0-1)"""
    score = 0.0
    
    # Required fields scoring
    if data.get('company'):
        score += 0.3
    if data.get('email'):
        score += 0.2
    if data.get('phone'):
        score += 0.15
    if data.get('website'):
        score += 0.1
    
    # Optional but valuable fields
    if data.get('industry'):
        score += 0.1
    if data.get('location'):
        score += 0.05
    if data.get('description'):
        score += 0.05
    if data.get('contact'):
        score += 0.05
    
    return min(score, 1.0)

def generate_search_suggestions(query: str) -> List[str]:
    """Generate search suggestions based on query"""
    if not query or len(query) < 2:
        return []
    
    suggestions = []
    query_lower = query.lower()
    
    # Industry-based suggestions
    industry_suggestions = {
        'tech': ['tecnologia', 'software', 'desenvolvimento', 'startup'],
        'rest': ['restaurante', 'comida', 'delivery', 'alimentação'],
        'saúde': ['clínica', 'hospital', 'médico', 'dentista'],
        'adv': ['advogado', 'escritório jurídico', 'advocacia'],
        'cont': ['contador', 'contabilidade', 'escritório contábil']
    }
    
    for key, terms in industry_suggestions.items():
        if key in query_lower:
            suggestions.extend([f"{query} {term}" for term in terms if term not in query_lower])
    
    # Location-based suggestions
    if any(city in query_lower for city in ['são paulo', 'rio', 'belo horizonte']):
        suggestions.append(f"{query} centro")
        suggestions.append(f"{query} zona sul")
    
    return suggestions[:5]  # Limit to 5 suggestions