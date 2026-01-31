"""
Configuration settings for the PDF Email Extractor application.
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# File upload settings
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf"}

# Processing settings
AUTO_DELETE_AFTER_SECONDS = 3600  # 1 hour
ENABLE_OCR = True
OCR_LANGUAGE = "eng"

# Email validation settings
ENABLE_DNS_LOOKUP = False  # Set to True for MX record validation
DNS_TIMEOUT = 5  # seconds

# Email blacklist - emails matching these patterns will be discarded
EMAIL_BLACKLIST = [
    "test@test.com",
    "example@example.com",
    "admin@localhost",
    "noreply@localhost",
]

# Domain blacklist - emails from these domains will be discarded
DOMAIN_BLACKLIST = [
    "localhost",
    "example.com",
    "test.com",
    "invalid.com",
]

# Known valid domains for confidence scoring
KNOWN_VALID_DOMAINS = [
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "aol.com",
    "protonmail.com",
    "mail.com",
    "zoho.com",
    "yandex.com",
]

# Rate limiting
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_PERIOD = 60  # seconds

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
