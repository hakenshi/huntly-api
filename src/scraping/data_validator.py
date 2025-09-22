"""
Data validation and cleaning utilities for scraped leads
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime

from .models import ScrapedLead, LeadValidationResult

logger = logging.getLogger(__name__)

class LeadDataValidator:
    """Validator for scraped lead data quality and completeness"""
    
    def __init__(self):
        # Brazilian business domains that are likely legitimate
        self.business_domains = {
            '.com.br', '.org.br', '.net.br', '.gov.br', '.edu.br',
            '.com', '.org', '.net', '.biz', '.info'
        }
        
        # Personal email domains to flag
        self.personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'uol.com.br', 'terra.com.br', 'bol.com.br', 'ig.com.br',
            'globo.com', 'r7.com'
        }
        
        # Common business suffixes in Brazil
        self.business_suffixes = {
            'ltda', 'ltd', 'inc', 'corp', 'sa', 's.a.', 'me', 'mei',
            'eireli', 'epp', 'llc', 'sociedade', 'empresa', 'companhia'
        }
    
    def validate_lead(self, lead: ScrapedLead) -> LeadValidationResult:
        """
        Comprehensive validation of a scraped lead
        
        Args:
            lead: ScrapedLead object to validate
            
        Returns:
            LeadValidationResult with validation details
        """
        issues = []
        suggestions = []
        enhanced_data = {}
        confidence_score = 0.0
        
        # Validate company name
        company_score, company_issues = self._validate_company_name(lead.company)
        confidence_score += company_score * 0.3
        issues.extend(company_issues)
        
        # Validate email
        email_score, email_issues, email_enhanced = self._validate_email(lead.email)
        confidence_score += email_score * 0.25
        issues.extend(email_issues)
        enhanced_data.update(email_enhanced)
        
        # Validate phone
        phone_score, phone_issues, phone_enhanced = self._validate_phone(lead.phone)
        confidence_score += phone_score * 0.2
        issues.extend(phone_issues)
        enhanced_data.update(phone_enhanced)
        
        # Validate website
        website_score, website_issues, website_enhanced = self._validate_website(lead.website)
        confidence_score += website_score * 0.15
        issues.extend(website_issues)
        enhanced_data.update(website_enhanced)
        
        # Validate location
        location_score, location_issues = self._validate_location(lead.location)
        confidence_score += location_score * 0.1
        issues.extend(location_issues)
        
        # Generate suggestions based on issues
        suggestions = self._generate_suggestions(issues, lead)
        
        # Determine if lead is valid (minimum threshold)
        is_valid = confidence_score >= 0.4 and lead.company and len(lead.company.strip()) >= 2
        
        return LeadValidationResult(
            is_valid=is_valid,
            confidence_score=min(confidence_score, 1.0),
            issues=issues,
            suggestions=suggestions,
            enhanced_data=enhanced_data
        )
    
    def _validate_company_name(self, company: str) -> Tuple[float, List[str]]:
        """Validate company name"""
        issues = []
        score = 0.0
        
        if not company:
            issues.append("Missing company name")
            return score, issues
        
        company = company.strip()
        
        if len(company) < 2:
            issues.append("Company name too short")
            return score, issues
        
        if len(company) > 100:
            issues.append("Company name unusually long")
            score += 0.5
        else:
            score += 0.8
        
        # Check for suspicious patterns
        if company.lower() in ['test', 'example', 'sample', 'demo']:
            issues.append("Company name appears to be placeholder")
            score = 0.1
        
        # Check if it looks like a real business name
        if any(suffix in company.lower() for suffix in self.business_suffixes):
            score += 0.2  # Bonus for business suffix
        
        return min(score, 1.0), issues
    
    def _validate_email(self, email: str) -> Tuple[float, List[str], Dict[str, Any]]:
        """Validate email address"""
        issues = []
        enhanced = {}
        score = 0.0
        
        if not email:
            return score, issues, enhanced
        
        email = email.strip().lower()
        
        # Basic format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            issues.append("Invalid email format")
            return score, issues, enhanced
        
        score += 0.5  # Valid format
        
        # Extract domain
        domain = email.split('@')[1]
        enhanced['email_domain'] = domain
        
        # Check if it's a business email
        if domain in self.personal_domains:
            issues.append("Personal email domain detected")
            score = 0.3  # Lower score for personal emails
        else:
            score += 0.5  # Bonus for business domain
            enhanced['is_business_email'] = True
        
        # Check for common non-business patterns
        local_part = email.split('@')[0]
        if any(pattern in local_part for pattern in ['noreply', 'no-reply', 'test', 'admin']):
            issues.append("Email appears to be system/admin email")
            score = 0.2
        
        return min(score, 1.0), issues, enhanced
    
    def _validate_phone(self, phone: str) -> Tuple[float, List[str], Dict[str, Any]]:
        """Validate phone number"""
        issues = []
        enhanced = {}
        score = 0.0
        
        if not phone:
            return score, issues, enhanced
        
        phone = phone.strip()
        
        # Remove formatting to check digits
        digits_only = re.sub(r'[^\d]', '', phone)
        
        if len(digits_only) < 8:
            issues.append("Phone number too short")
            return score, issues, enhanced
        
        if len(digits_only) > 15:
            issues.append("Phone number too long")
            return score, issues, enhanced
        
        score += 0.6  # Valid length
        
        # Check Brazilian phone patterns
        brazilian_patterns = [
            r'\+55\s*\d{2}\s*\d{4,5}-?\d{4}',  # +55 XX XXXXX-XXXX
            r'\(\d{2}\)\s*\d{4,5}-?\d{4}',     # (XX) XXXXX-XXXX
            r'\d{2}\s*\d{4,5}-?\d{4}'          # XX XXXXX-XXXX
        ]
        
        for pattern in brazilian_patterns:
            if re.match(pattern, phone):
                score += 0.4  # Bonus for proper format
                enhanced['phone_format'] = 'brazilian'
                break
        
        # Extract area code if present
        area_code_match = re.search(r'(\d{2})', digits_only)
        if area_code_match:
            area_code = area_code_match.group(1)
            enhanced['area_code'] = area_code
            
            # Validate Brazilian area codes
            valid_area_codes = [
                '11', '12', '13', '14', '15', '16', '17', '18', '19',  # SP
                '21', '22', '24',  # RJ
                '27', '28',  # ES
                '31', '32', '33', '34', '35', '37', '38',  # MG
                '41', '42', '43', '44', '45', '46',  # PR
                '47', '48', '49',  # SC
                '51', '53', '54', '55',  # RS
                '61',  # DF
                '62', '64',  # GO
                '63',  # TO
                '65', '66',  # MT
                '67',  # MS
                '68',  # AC
                '69',  # RO
                '71', '73', '74', '75', '77',  # BA
                '79',  # SE
                '81', '87',  # PE
                '82',  # AL
                '83',  # PB
                '84',  # RN
                '85', '88',  # CE
                '86', '89',  # PI
                '91', '93', '94',  # PA
                '92', '97',  # AM
                '95',  # RR
                '96',  # AP
                '98', '99'   # MA
            ]
            
            if area_code in valid_area_codes:
                score += 0.2  # Bonus for valid area code
                enhanced['valid_area_code'] = True
            else:
                issues.append(f"Invalid Brazilian area code: {area_code}")
        
        return min(score, 1.0), issues, enhanced
    
    def _validate_website(self, website: str) -> Tuple[float, List[str], Dict[str, Any]]:
        """Validate website URL"""
        issues = []
        enhanced = {}
        score = 0.0
        
        if not website:
            return score, issues, enhanced
        
        website = str(website).strip()
        
        try:
            parsed = urlparse(website)
            
            if not parsed.scheme:
                issues.append("Missing URL scheme (http/https)")
                return score, issues, enhanced
            
            if parsed.scheme not in ['http', 'https']:
                issues.append("Invalid URL scheme")
                return score, issues, enhanced
            
            if not parsed.netloc:
                issues.append("Missing domain in URL")
                return score, issues, enhanced
            
            score += 0.6  # Valid URL structure
            
            domain = parsed.netloc.lower()
            enhanced['website_domain'] = domain
            
            # Remove www prefix for analysis
            clean_domain = domain.replace('www.', '')
            
            # Check if it's a business domain
            if any(tld in clean_domain for tld in self.business_domains):
                score += 0.3
                enhanced['business_domain'] = True
            
            # Check for suspicious domains
            suspicious_domains = [
                'google.com', 'facebook.com', 'linkedin.com', 'twitter.com',
                'instagram.com', 'youtube.com', 'wikipedia.org'
            ]
            
            if any(sus_domain in clean_domain for sus_domain in suspicious_domains):
                issues.append("Website appears to be social media or search engine")
                score = 0.2
            
            # Bonus for HTTPS
            if parsed.scheme == 'https':
                score += 0.1
                enhanced['secure_website'] = True
            
        except Exception as e:
            issues.append(f"Invalid URL format: {str(e)}")
            return 0.0, issues, enhanced
        
        return min(score, 1.0), issues, enhanced
    
    def _validate_location(self, location: str) -> Tuple[float, List[str]]:
        """Validate location information"""
        issues = []
        score = 0.0
        
        if not location:
            return score, issues
        
        location = location.strip()
        
        if len(location) < 2:
            issues.append("Location too short")
            return score, issues
        
        score += 0.5  # Has location
        
        # Check for Brazilian location patterns
        brazilian_states = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
            'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
            'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        
        location_upper = location.upper()
        if any(state in location_upper for state in brazilian_states):
            score += 0.3  # Bonus for Brazilian state
        
        # Check for major Brazilian cities
        major_cities = [
            'São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Brasília',
            'Salvador', 'Fortaleza', 'Curitiba', 'Recife', 'Porto Alegre'
        ]
        
        if any(city.lower() in location.lower() for city in major_cities):
            score += 0.2  # Bonus for major city
        
        return min(score, 1.0), issues
    
    def _generate_suggestions(self, issues: List[str], lead: ScrapedLead) -> List[str]:
        """Generate suggestions based on validation issues"""
        suggestions = []
        
        if "Missing company name" in issues:
            suggestions.append("Try to extract company name from website title or domain")
        
        if "Personal email domain detected" in issues:
            suggestions.append("Look for alternative business email on company website")
        
        if "Invalid email format" in issues:
            suggestions.append("Verify email format and try alternative extraction methods")
        
        if "Phone number too short" in issues or "Phone number too long" in issues:
            suggestions.append("Validate phone number format and try alternative extraction")
        
        if "Missing URL scheme" in issues:
            suggestions.append("Add http:// or https:// prefix to website URL")
        
        if not lead.email and not lead.phone:
            suggestions.append("Lead has no contact information - consider skipping or finding alternative sources")
        
        return suggestions

# Global validator instance
lead_validator = LeadDataValidator()