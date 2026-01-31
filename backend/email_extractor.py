"""
Email Extractor Module
Handles extraction of email addresses from text, including de-obfuscation
and context awareness.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmailExtractor:
    """
    Extract email addresses from text content with smart de-obfuscation
    and context extraction.
    """
    
    # Comprehensive email regex pattern
    EMAIL_PATTERN = re.compile(
        r'''
        (?P<email>
            [a-zA-Z0-9._%+\-]+      # Local part
            @                        # @ symbol
            [a-zA-Z0-9.\-]+         # Domain
            \.                       # Dot
            [a-zA-Z]{2,}            # TLD (2+ chars)
        )
        ''',
        re.VERBOSE | re.IGNORECASE
    )
    
    # Pattern to capture email with surrounding context
    EMAIL_WITH_CONTEXT_PATTERN = re.compile(
        r'''
        (?P<context_before>.{0,100}?)   # Up to 100 chars before
        (?P<email>
            [a-zA-Z0-9._%+\-]+
            @
            [a-zA-Z0-9.\-]+
            \.
            [a-zA-Z]{2,}
        )
        (?P<context_after>.{0,100}?)    # Up to 100 chars after
        ''',
        re.VERBOSE | re.IGNORECASE | re.DOTALL
    )
    
    # Obfuscation patterns to normalize
    OBFUSCATION_REPLACEMENTS = [
        # @ symbol variants
        (r'\s*\[\s*at\s*\]\s*', '@'),
        (r'\s*\(\s*at\s*\)\s*', '@'),
        (r'\s*\{\s*at\s*\}\s*', '@'),
        (r'\s+at\s+', '@'),
        (r'\s*<\s*at\s*>\s*', '@'),
        (r'\s*@\s*', '@'),
        
        # Dot variants
        (r'\s*\[\s*dot\s*\]\s*', '.'),
        (r'\s*\(\s*dot\s*\)\s*', '.'),
        (r'\s*\{\s*dot\s*\}\s*', '.'),
        (r'\s+dot\s+', '.'),
        (r'\s*<\s*dot\s*>\s*', '.'),
        
        # Underscore variants
        (r'\s*\[\s*underscore\s*\]\s*', '_'),
        (r'\s*\(\s*underscore\s*\)\s*', '_'),
        
        # Dash variants
        (r'\s*\[\s*dash\s*\]\s*', '-'),
        (r'\s*\(\s*dash\s*\)\s*', '-'),
    ]
    
    # Name extraction patterns (common patterns before emails)
    NAME_PATTERNS = [
        r'(?P<name>[A-Z][a-z]+\s+[A-Z][a-z]+)\s*[-–:]\s*$',  # "John Doe -" or "John Doe:"
        r'(?P<name>[A-Z][a-z]+\s+[A-Z][a-z]+)\s*$',  # "John Doe" (right before email)
        r'(?:Name|Contact|From|Author)[\s:]+(?P<name>[A-Z][a-zA-Z\s]+)',
        r'(?P<name>Dr\.|Mr\.|Ms\.|Mrs\.\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    
    def __init__(self):
        """Initialize the email extractor."""
        self.compiled_obfuscation = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.OBFUSCATION_REPLACEMENTS
        ]
        self.compiled_name_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.NAME_PATTERNS
        ]
    
    def extract_emails(self, text: str) -> list[dict]:
        """
        Extract email addresses from text.
        
        Args:
            text: The text content to extract emails from
            
        Returns:
            List of dictionaries containing email and metadata
        """
        if not text:
            return []
        
        # First, de-obfuscate the text
        normalized_text = self._de_obfuscate(text)
        
        # Extract emails with context
        emails_found = []
        seen_emails = set()
        
        # Find all matches with context
        for match in self.EMAIL_WITH_CONTEXT_PATTERN.finditer(normalized_text):
            raw_email = match.group('email')
            
            # Normalize the email
            email = self._normalize_email(raw_email)
            
            # Skip duplicates
            if email in seen_emails:
                continue
            
            # Skip invalid-looking emails
            if not self._basic_validate(email):
                continue
            
            seen_emails.add(email)
            
            # Extract context
            context_before = match.group('context_before').strip()
            context_after = match.group('context_after').strip()
            full_context = f"{context_before} [EMAIL] {context_after}".strip()
            
            # Try to extract name hint
            name_hint = self._extract_name_hint(context_before, context_after)
            
            # Try to extract company hint
            company_hint = self._extract_company_hint(context_before, context_after, email)
            
            emails_found.append({
                'email': email,
                'raw_email': raw_email,
                'context': full_context[:200] if full_context else None,
                'name_hint': name_hint,
                'company_hint': company_hint
            })
        
        logger.info(f"Extracted {len(emails_found)} unique emails from text")
        return emails_found
    
    def _de_obfuscate(self, text: str) -> str:
        """
        De-obfuscate text by replacing common obfuscation patterns.
        
        Examples:
            - "john [at] gmail [dot] com" -> "john@gmail.com"
            - "john(at)gmail.com" -> "john@gmail.com"
        """
        result = text
        
        for pattern, replacement in self.compiled_obfuscation:
            result = pattern.sub(replacement, result)
        
        return result
    
    def _normalize_email(self, email: str) -> str:
        """
        Normalize an email address.
        
        - Convert to lowercase
        - Remove leading/trailing whitespace
        - Remove surrounding punctuation
        """
        email = email.lower().strip()
        
        # Remove common surrounding punctuation
        email = email.strip('.,;:!?\'"<>()[]{}')
        
        # Remove any remaining whitespace
        email = ''.join(email.split())
        
        return email
    
    def _basic_validate(self, email: str) -> bool:
        """
        Basic validation to filter out obvious non-emails.
        """
        if not email or len(email) < 5:
            return False
        
        if '@' not in email:
            return False
        
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        
        # Local part checks
        if not local or len(local) > 64:
            return False
        
        # Domain checks
        if not domain or '.' not in domain:
            return False
        
        # TLD check
        tld = domain.split('.')[-1]
        if len(tld) < 2 or not tld.isalpha():
            return False
        
        return True
    
    def _extract_name_hint(self, before: str, after: str) -> Optional[str]:
        """
        Try to extract a name from the context around the email.
        """
        # Check context before the email first
        for pattern in self.compiled_name_patterns:
            match = pattern.search(before)
            if match:
                try:
                    name = match.group('name').strip()
                    if name and len(name) > 2:
                        return name
                except (IndexError, AttributeError):
                    continue
        
        # Also try to infer from email itself
        # E.g., john.doe@gmail.com -> John Doe
        # This is handled in validator for confidence scoring
        
        return None
    
    def _extract_company_hint(self, before: str, after: str, email: str) -> Optional[str]:
        """
        Try to extract a company name from context or email domain.
        """
        context = f"{before} {after}"
        
        # Common company indicators
        company_patterns = [
            r'(?:Company|Organization|Org|Corp|Inc|Ltd)[\s:]+([A-Z][A-Za-z\s]+)',
            r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+(?:Pvt\.?\s+Ltd\.?|Inc\.?|Corp\.?|LLC)',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                if company and len(company) > 2:
                    return company
        
        # Infer from email domain if it's not a common email provider
        domain = email.split('@')[1] if '@' in email else None
        if domain:
            common_providers = {
                'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                'icloud.com', 'aol.com', 'mail.com', 'protonmail.com'
            }
            if domain not in common_providers:
                # Extract company name from domain
                company_part = domain.split('.')[0]
                if len(company_part) > 2:
                    return company_part.replace('-', ' ').replace('_', ' ').title()
        
        return None
    
    def extract_emails_simple(self, text: str) -> list[str]:
        """
        Simple extraction that returns only email strings.
        Useful for quick extraction without context.
        """
        if not text:
            return []
        
        normalized_text = self._de_obfuscate(text)
        emails = set()
        
        for match in self.EMAIL_PATTERN.finditer(normalized_text):
            email = self._normalize_email(match.group('email'))
            if self._basic_validate(email):
                emails.add(email)
        
        return sorted(list(emails))
    
    def extract_emails_with_duplicates(self, text: str) -> list[dict]:
        """
        Extract email addresses from text WITHOUT removing duplicates.
        This allows tracking of duplicate emails across the document.
        
        Args:
            text: The text content to extract emails from
            
        Returns:
            List of dictionaries containing email and metadata (may contain duplicates)
        """
        if not text:
            return []
        
        # First, de-obfuscate the text
        normalized_text = self._de_obfuscate(text)
        
        # Extract all emails (including duplicates)
        emails_found = []
        seen_positions = set()  # Track email positions to avoid overlapping matches
        
        # Find all matches with context
        for match in self.EMAIL_WITH_CONTEXT_PATTERN.finditer(normalized_text):
            raw_email = match.group('email')
            email_start = match.start('email')
            email_end = match.end('email')
            
            # Skip if we've already processed this exact position
            if email_start in seen_positions:
                continue
            seen_positions.add(email_start)
            
            # Normalize the email
            email = self._normalize_email(raw_email)
            
            # Skip invalid-looking emails
            if not self._basic_validate(email):
                continue
            
            # Extract context
            context_before = match.group('context_before').strip()
            context_after = match.group('context_after').strip()
            full_context = f"{context_before} [EMAIL] {context_after}".strip()
            
            # Try to extract name hint
            name_hint = self._extract_name_hint(context_before, context_after)
            
            # Try to extract company hint
            company_hint = self._extract_company_hint(context_before, context_after, email)
            
            emails_found.append({
                'email': email,
                'raw_email': raw_email,
                'context': full_context[:200] if full_context else None,
                'name_hint': name_hint,
                'company_hint': company_hint
            })
        
        logger.info(f"Extracted {len(emails_found)} emails (with duplicates) from text")
        return emails_found


# Command-line testing
if __name__ == "__main__":
    test_texts = [
        "Contact us at support@example.com for help.",
        "John Doe - john.doe@gmail.com",
        "Email: test [at] domain [dot] com",
        "Reach me at alice(at)company.org or bob [at] gmail [dot] com",
        "Multiple: a@b.com, c@d.org, e@f.net",
        "Invalid: @nodomain, noatsign.com, missing@tld",
    ]
    
    extractor = EmailExtractor()
    
    for text in test_texts:
        print(f"\nInput: {text}")
        results = extractor.extract_emails(text)
        for r in results:
            print(f"  Found: {r['email']}")
            if r.get('name_hint'):
                print(f"    Name: {r['name_hint']}")
