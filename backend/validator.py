"""
Email Validator Module
Validates email addresses using multiple layers: syntax, domain, DNS/MX.
Provides confidence scoring for each email.
"""
import re
import socket
import logging
from typing import Optional
from functools import lru_cache

from .config import (
    ENABLE_DNS_LOOKUP, DNS_TIMEOUT, 
    EMAIL_BLACKLIST, DOMAIN_BLACKLIST, KNOWN_VALID_DOMAINS
)

logger = logging.getLogger(__name__)


class EmailValidator:
    """
    Multi-layer email validation with confidence scoring.
    """
    
    # RFC 5322 compliant email regex (simplified)
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+'
        r'@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )
    
    # Valid TLDs (top-level domains) - common ones
    VALID_TLDS = {
        # Generic TLDs
        'com', 'org', 'net', 'edu', 'gov', 'mil', 'int',
        'info', 'biz', 'name', 'pro', 'aero', 'coop', 'museum',
        'jobs', 'travel', 'mobi', 'cat', 'tel', 'asia',
        # New gTLDs
        'app', 'dev', 'io', 'co', 'ai', 'tech', 'online', 'store',
        'site', 'cloud', 'digital', 'email', 'company', 'business',
        # Country codes (common ones)
        'us', 'uk', 'ca', 'au', 'de', 'fr', 'jp', 'cn', 'in', 'br',
        'ru', 'it', 'es', 'nl', 'se', 'no', 'dk', 'fi', 'pl', 'cz',
        'at', 'ch', 'be', 'ie', 'nz', 'sg', 'hk', 'kr', 'mx', 'ar',
        'za', 'ae', 'il', 'tr', 'gr', 'pt', 'hu', 'ro', 'ua', 'th',
        'my', 'ph', 'id', 'vn', 'pk', 'eg', 'ng', 'ke', 'gh',
    }
    
    def __init__(self, enable_dns: Optional[bool] = None):
        """
        Initialize the email validator.
        
        Args:
            enable_dns: Override config for DNS lookup
        """
        self.enable_dns = enable_dns if enable_dns is not None else ENABLE_DNS_LOOKUP
        self.dns_timeout = DNS_TIMEOUT
    
    def validate(self, email: str) -> dict:
        """
        Validate an email address with multiple checks.
        
        Args:
            email: The email address to validate
            
        Returns:
            Dictionary with validation results and confidence score
        """
        result = {
            'email': email,
            'is_valid': False,
            'confidence': 0.0,
            'domain': '',
            'details': {
                'syntax_valid': False,
                'domain_valid': False,
                'tld_valid': False,
                'not_blacklisted': False,
                'mx_exists': None,
                'issues': []
            }
        }
        
        if not email:
            result['details']['issues'].append('Empty email')
            return result
        
        # Extract domain
        try:
            local_part, domain = email.rsplit('@', 1)
            result['domain'] = domain.lower()
        except ValueError:
            result['details']['issues'].append('Invalid format - no @ symbol')
            return result
        
        confidence = 0.0
        
        # 1. Syntax validation (30 points)
        syntax_check = self._validate_syntax(email)
        result['details']['syntax_valid'] = syntax_check['valid']
        if syntax_check['valid']:
            confidence += 30
        else:
            result['details']['issues'].extend(syntax_check['issues'])
        
        # 2. Domain structure validation (20 points)
        domain_check = self._validate_domain(domain)
        result['details']['domain_valid'] = domain_check['valid']
        if domain_check['valid']:
            confidence += 20
        else:
            result['details']['issues'].extend(domain_check['issues'])
        
        # 3. TLD validation (15 points)
        tld_check = self._validate_tld(domain)
        result['details']['tld_valid'] = tld_check['valid']
        if tld_check['valid']:
            confidence += 15
        else:
            result['details']['issues'].extend(tld_check['issues'])
        
        # 4. Blacklist check (15 points)
        blacklist_check = self._check_blacklist(email, domain)
        result['details']['not_blacklisted'] = blacklist_check['valid']
        if blacklist_check['valid']:
            confidence += 15
        else:
            result['details']['issues'].extend(blacklist_check['issues'])
        
        # 5. Known domain bonus (10 points)
        if domain.lower() in KNOWN_VALID_DOMAINS:
            confidence += 10
        
        # 6. DNS/MX lookup (10 points, optional)
        if self.enable_dns and confidence >= 50:  # Only check if likely valid
            mx_check = self._check_mx_record(domain)
            result['details']['mx_exists'] = mx_check['valid']
            if mx_check['valid']:
                confidence += 10
            elif mx_check['valid'] is False:  # Explicitly failed (not just skipped)
                confidence -= 5
                result['details']['issues'].append('No MX record found')
        
        # Set final confidence and validity
        result['confidence'] = min(100, max(0, confidence))
        result['is_valid'] = (
            result['details']['syntax_valid'] and 
            result['details']['domain_valid'] and
            result['details']['not_blacklisted'] and
            confidence >= 50
        )
        
        return result
    
    def _validate_syntax(self, email: str) -> dict:
        """Validate email syntax using regex."""
        result = {'valid': False, 'issues': []}
        
        # Length checks
        if len(email) > 254:
            result['issues'].append('Email too long (max 254 chars)')
            return result
        
        try:
            local_part, domain = email.rsplit('@', 1)
        except ValueError:
            result['issues'].append('Missing @ symbol')
            return result
        
        # Local part checks
        if not local_part:
            result['issues'].append('Empty local part')
            return result
        
        if len(local_part) > 64:
            result['issues'].append('Local part too long (max 64 chars)')
            return result
        
        if local_part.startswith('.') or local_part.endswith('.'):
            result['issues'].append('Local part cannot start or end with a dot')
            return result
        
        if '..' in local_part:
            result['issues'].append('Local part contains consecutive dots')
            return result
        
        # Regex check
        if not self.EMAIL_REGEX.match(email):
            result['issues'].append('Invalid characters or format')
            return result
        
        result['valid'] = True
        return result
    
    def _validate_domain(self, domain: str) -> dict:
        """Validate domain structure."""
        result = {'valid': False, 'issues': []}
        
        if not domain:
            result['issues'].append('Empty domain')
            return result
        
        # Length check
        if len(domain) > 255:
            result['issues'].append('Domain too long')
            return result
        
        # Must contain at least one dot
        if '.' not in domain:
            result['issues'].append('Domain must contain a dot')
            return result
        
        # Split into labels
        labels = domain.split('.')
        
        for label in labels:
            if not label:
                result['issues'].append('Empty label in domain')
                return result
            
            if len(label) > 63:
                result['issues'].append(f'Label too long: {label}')
                return result
            
            if label.startswith('-') or label.endswith('-'):
                result['issues'].append('Label cannot start or end with hyphen')
                return result
            
            # Must be alphanumeric with hyphens
            if not re.match(r'^[a-zA-Z0-9-]+$', label):
                result['issues'].append(f'Invalid characters in label: {label}')
                return result
        
        result['valid'] = True
        return result
    
    def _validate_tld(self, domain: str) -> dict:
        """Validate top-level domain."""
        result = {'valid': False, 'issues': []}
        
        tld = domain.split('.')[-1].lower()
        
        if not tld:
            result['issues'].append('Empty TLD')
            return result
        
        if len(tld) < 2:
            result['issues'].append('TLD too short')
            return result
        
        # Check if it's all numeric (invalid)
        if tld.isdigit():
            result['issues'].append('TLD cannot be all numbers')
            return result
        
        # Check against known TLDs (not strict - allow unknown TLDs with warning)
        if tld not in self.VALID_TLDS:
            # Still valid, but might be less common
            result['issues'].append(f'Uncommon TLD: .{tld}')
        
        result['valid'] = True
        return result
    
    def _check_blacklist(self, email: str, domain: str) -> dict:
        """Check email and domain against blacklists."""
        result = {'valid': True, 'issues': []}
        
        email_lower = email.lower()
        domain_lower = domain.lower()
        
        # Check email blacklist
        if email_lower in [e.lower() for e in EMAIL_BLACKLIST]:
            result['valid'] = False
            result['issues'].append('Email is blacklisted')
            return result
        
        # Check domain blacklist
        if domain_lower in [d.lower() for d in DOMAIN_BLACKLIST]:
            result['valid'] = False
            result['issues'].append(f'Domain is blacklisted: {domain}')
            return result
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'^test\d*@',
            r'^example\d*@',
            r'^admin@(?!real)',
            r'^no-?reply@',
            r'^spam@',
            r'^fake@',
        ]
        
        for pattern in suspicious_patterns:
            if re.match(pattern, email_lower):
                result['issues'].append('Suspicious email pattern')
                # Don't invalidate, just note it
                break
        
        return result
    
    @lru_cache(maxsize=1000)
    def _check_mx_record(self, domain: str) -> dict:
        """Check if domain has MX records (cached)."""
        result = {'valid': None, 'issues': []}
        
        try:
            import dns.resolver
            
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.dns_timeout
            resolver.lifetime = self.dns_timeout
            
            try:
                mx_records = resolver.resolve(domain, 'MX')
                if mx_records:
                    result['valid'] = True
                    return result
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                # Try A record as fallback
                try:
                    a_records = resolver.resolve(domain, 'A')
                    if a_records:
                        result['valid'] = True
                        result['issues'].append('No MX record, but A record exists')
                        return result
                except:
                    pass
            
            result['valid'] = False
            result['issues'].append('Domain has no mail server')
            
        except ImportError:
            # dnspython not installed
            result['valid'] = None
            result['issues'].append('DNS lookup unavailable')
            logger.debug("dnspython not installed, skipping MX check")
            
        except Exception as e:
            result['valid'] = None
            result['issues'].append(f'DNS lookup error: {str(e)}')
            logger.warning(f"DNS lookup error for {domain}: {e}")
        
        return result
    
    def validate_batch(self, emails: list[str]) -> list[dict]:
        """
        Validate multiple emails.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of validation results
        """
        return [self.validate(email) for email in emails]
    
    def get_confidence_label(self, confidence: float) -> str:
        """Get a human-readable label for confidence score."""
        if confidence >= 90:
            return "Very High"
        elif confidence >= 75:
            return "High"
        elif confidence >= 50:
            return "Medium"
        elif confidence >= 25:
            return "Low"
        else:
            return "Very Low"


# Command-line testing
if __name__ == "__main__":
    test_emails = [
        "john.doe@gmail.com",
        "test@test.com",
        "invalid@",
        "@nodomain.com",
        "user@localhost",
        "valid.email+tag@company.org",
        "bad..email@domain.com",
        "good@unknown-domain.xyz",
    ]
    
    validator = EmailValidator(enable_dns=False)
    
    for email in test_emails:
        result = validator.validate(email)
        print(f"\n{email}")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Confidence: {result['confidence']:.1f}%")
        if result['details']['issues']:
            print(f"  Issues: {', '.join(result['details']['issues'])}")
