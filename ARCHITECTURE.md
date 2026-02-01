# PDF Email Extractor - Project Architecture & Blueprint

## 📁 Project Structure

```
email extract/
├── backend/                    # Python FastAPI Backend
│   ├── main.py                # API endpoints & server setup
│   ├── pdf_processor.py       # PDF text extraction & OCR
│   ├── email_extractor.py     # Email pattern matching & extraction
│   ├── validator.py           # Email validation (syntax, DNS, disposable check)
│   └── config.py              # Configuration settings
│
├── frontend/                   # Vanilla JavaScript Frontend
│   ├── index.html             # Main HTML structure
│   ├── styles.css             # All CSS styling
│   └── app.js                 # Frontend logic & API calls
│
├── eg email/                   # Sample PDF files for testing
│
├── Dockerfile                  # Docker container configuration
├── render.yaml                 # Render.com deployment config
├── .dockerignore              # Docker build exclusions
├── requirements.txt           # Python dependencies
└── ARCHITECTURE.md            # This file
```

---

## 🔄 Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   User      │────▶│   Frontend  │────▶│   Backend API   │────▶│   Response  │
│ Upload PDF  │     │   app.js    │     │    main.py      │     │   JSON      │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
            ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
            │ PDFProcessor  │         │EmailExtractor │         │   Validator   │
            │pdf_processor.py│        │email_extractor│         │ validator.py  │
            └───────────────┘         └───────────────┘         └───────────────┘
```

---

## 📝 File Responsibilities

### Backend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `main.py` | FastAPI server, routes, async processing | `upload_pdf()`, `get_results()`, `process_pdf_task()` |
| `pdf_processor.py` | Extract text from PDFs (native + OCR) | `extract_text()`, `_extract_with_ocr()`, `_ocr_with_preprocessing()` |
| `email_extractor.py` | Find emails in text using regex | `extract_emails()`, `_clean_email()` |
| `validator.py` | Validate emails (syntax, DNS, disposable) | `validate_email()`, `_check_dns()`, `_is_disposable()` |
| `config.py` | Central configuration | All settings and constants |

### Frontend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `index.html` | Page structure, sections | Upload area, results table, charts |
| `styles.css` | Visual styling | Responsive design, animations |
| `app.js` | All interactivity | `uploadFile()`, `pollResults()`, `displayResults()`, `exportEmails()` |

---

## 🔧 Common Modifications Guide

### 1. Change Email Validation Rules

**File:** `backend/validator.py`

```python
# Add new disposable domains (line ~50)
DISPOSABLE_DOMAINS = {
    "tempmail.com",
    "your-new-domain.com",  # Add here
    ...
}

# Modify syntax validation regex (line ~150)
EMAIL_REGEX = r"..."  # Modify pattern here

# Change confidence scoring (line ~200)
def _calculate_confidence():
    # Adjust scoring weights here
```

### 2. Modify OCR Settings

**File:** `backend/pdf_processor.py`

```python
# Change OCR resolution (line ~195)
pix = page.get_pixmap(matrix=self.fitz.Matrix(4, 4))  # 4x zoom
# Lower = faster but less accurate, Higher = slower but more accurate

# Add/remove OCR strategies (line ~250 in _ocr_with_preprocessing)
# Strategy 1: OTSU - good for clear docs
# Strategy 2: Adaptive - good for varied lighting
# Strategy 3: Grayscale - catches edge cases

# Change OCR language (line ~27)
def __init__(self, enable_ocr=True, ocr_language="eng"):
    # Change "eng" to other language codes like "fra", "deu", "spa"
```

### 3. Add New Export Format

**File:** `frontend/app.js`

```javascript
// Find exportEmails function (~line 800)
function exportEmails(format) {
    switch(format) {
        case 'csv': ...
        case 'json': ...
        case 'txt': ...
        // Add new format here:
        case 'xml':
            content = generateXML(emails);
            mimeType = 'application/xml';
            break;
    }
}
```

### 4. Change UI Colors/Theme

**File:** `frontend/styles.css`

```css
/* Primary colors (top of file) */
:root {
    --primary-color: #667eea;      /* Main purple */
    --secondary-color: #764ba2;    /* Gradient end */
    --success-color: #48bb78;      /* Green for valid */
    --danger-color: #f56565;       /* Red for invalid */
    --warning-color: #ed8936;      /* Orange for warnings */
}
```

### 5. Modify Processing Timeout

**File:** `frontend/app.js`

```javascript
// Line ~338
const maxAttempts = 120;  // 120 attempts x 2 seconds = 4 minutes
// Increase for larger files, decrease for faster timeout
```

**File:** `backend/config.py`

```python
DNS_TIMEOUT = 5  # DNS lookup timeout in seconds
```

### 6. Add New API Endpoint

**File:** `backend/main.py`

```python
# Add after existing routes (~line 150)
@app.get("/api/new-endpoint")
async def new_endpoint():
    return {"message": "New endpoint"}

# For POST with data:
@app.post("/api/process-something")
async def process_something(data: dict):
    # Your logic here
    return {"result": processed_data}
```

### 7. Change Pagination Settings

**File:** `frontend/app.js`

```javascript
// Line ~20
const ITEMS_PER_PAGE = 10;  // Change to show more/fewer items per page
```

### 8. Modify Email Extraction Pattern

**File:** `backend/email_extractor.py`

```python
# Main email regex pattern (line ~30)
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# To be more strict (require valid TLDs):
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|org|net|edu|...)'

# To allow more characters:
EMAIL_PATTERN = r'[a-zA-Z0-9._%+\-\']+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
```

---

## 🐛 Troubleshooting Guide

### Issue: OCR Not Working

**Symptoms:** Scanned PDFs return 0 emails

**Check:**
1. Tesseract installed? 
   - Windows: `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - Linux/Docker: `tesseract-ocr` package
2. Path configured in `pdf_processor.py` line ~55

**Fix:**
```python
# In pdf_processor.py _check_dependencies()
pytesseract.pytesseract.tesseract_cmd = r'C:\your\path\tesseract.exe'
```

### Issue: Processing Timeout

**Symptoms:** "Processing timed out" error

**Causes:**
- Large PDF files
- High-resolution OCR
- Slow server

**Fix:**
1. Increase timeout in `app.js` (maxAttempts)
2. Reduce OCR zoom in `pdf_processor.py`
3. Reduce OCR strategies (use fewer)

### Issue: No Emails Found (Text PDF)

**Symptoms:** PDF has visible emails but none extracted

**Check:**
1. PDF might be image-based (check with pdf_processor.get_pdf_info())
2. Email format might be unusual

**Fix:**
- Enable OCR: Set `enable_ocr=True` in PDFProcessor
- Modify EMAIL_PATTERN in email_extractor.py

### Issue: Invalid Emails Marked as Valid

**Symptoms:** Fake domains showing as valid

**Fix:**
1. Enable DNS lookup in `config.py`:
   ```python
   ENABLE_DNS_LOOKUP = True
   ```
2. Add to disposable domains list in `validator.py`

### Issue: Docker Build Fails

**Check:** `Dockerfile` for correct package names
- Debian Trixie uses `libgl1` not `libgl1-mesa-glx`

---

## 🚀 Deployment Checklist

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn backend.main:app --reload --port 8000

# Access at http://localhost:8000
```

### Docker Deployment
```bash
# Build image
docker build -t email-extractor .

# Run container
docker run -p 8000:8000 email-extractor
```

### Render.com Deployment
1. Push to GitHub
2. Connect repo to Render
3. Render uses `render.yaml` automatically
4. Environment: Docker

---

## 📊 Key Configuration (config.py)

```python
# Validation Settings
ENABLE_DNS_LOOKUP = False      # True = slower but more accurate
DNS_TIMEOUT = 5                # Seconds for DNS lookup

# Processing
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max upload

# Add custom settings here...
```

---

## 🔌 API Reference

### POST /upload
Upload a PDF file for processing.

**Request:** `multipart/form-data` with `file` field

**Response:**
```json
{
  "task_id": "uuid-string",
  "message": "Processing started"
}
```

### GET /results/{task_id}
Get processing results.

**Response (processing):**
```json
{
  "status": "processing",
  "progress": 50,
  "current_page": 2,
  "total_pages": 4
}
```

**Response (completed):**
```json
{
  "status": "completed",
  "total_emails": 100,
  "valid_emails": 85,
  "invalid_emails": 15,
  "emails": [...],
  "duplicates": [...],
  "processing_time": 5.2
}
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.109.0 | Web framework |
| uvicorn | 0.27.0 | ASGI server |
| pdfplumber | 0.10.3 | PDF text extraction |
| PyMuPDF | 1.23.8 | PDF rendering for OCR |
| pytesseract | 0.3.10 | OCR engine wrapper |
| Pillow | 10.2.0 | Image processing |
| opencv-python-headless | >=4.9.0 | Image preprocessing |
| dnspython | 2.4.2 | DNS lookups |

---

## 🎯 Future Enhancement Ideas

1. **Batch Processing** - Upload multiple PDFs at once
2. **Email Verification API** - SMTP verification for deliverability
3. **User Accounts** - Save extraction history
4. **API Keys** - Rate limiting and authentication
5. **Webhook Support** - Notify when processing completes
6. **More Export Formats** - Excel, vCard
7. **Email Templates** - Generate mailto links
8. **Statistics Dashboard** - Domain distribution, trends

---

## 👨‍💻 Quick Reference Commands

```bash
# Start development server
uvicorn backend.main:app --reload --port 8000

# Run with host binding (access from other devices)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Install single package
pip install package-name

# Update requirements
pip freeze > requirements.txt

# Docker build
docker build -t email-extractor .

# Docker run
docker run -p 8000:8000 email-extractor

# Git push to deploy
git add . && git commit -m "message" && git push
```

---

*Last Updated: February 2026*
