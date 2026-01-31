# PDF Email Extractor

A robust web application that extracts, validates, and exports email addresses from PDF files. Features intelligent de-obfuscation, confidence scoring, and support for both text-based and scanned PDFs.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🎯 Features

### Core Features
- **PDF Upload**: Drag-and-drop or file picker with multi-file support
- **Text Extraction**: Handles text-based and scanned PDFs (OCR)
- **Email Extraction**: Robust regex with de-obfuscation support
- **Email Validation**: Multi-layer validation with confidence scoring
- **Export**: CSV, TXT, and XLSX formats

### Smart Features
- **De-Obfuscation**: Handles `john [at] gmail [dot] com` formats
- **Confidence Scoring**: 0-100% score based on syntax, domain, MX records
- **Context Awareness**: Extracts names and company hints near emails
- **Unicode Support**: Handles PDFs with mixed languages

## 📁 Project Structure

```
email extract/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── pdf_processor.py     # PDF text extraction
│   ├── email_extractor.py   # Email extraction logic
│   ├── validator.py         # Email validation
│   └── utils/
│       ├── __init__.py
│       └── helpers.py       # Utility functions
├── frontend/
│   ├── index.html           # Main HTML page
│   ├── styles.css           # Styling
│   └── app.js               # Frontend JavaScript
├── uploads/                  # Temporary file storage
├── exports/                  # Export files
├── requirements.txt         # Python dependencies
├── instructions.md          # Project requirements
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Tesseract OCR (optional, for scanned PDFs)

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd "d:\programming exercise\projects\email extract"
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract OCR (optional, for scanned PDFs)**
   - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - **Linux**: `sudo apt install tesseract-ocr`
   - **Mac**: `brew install tesseract`

### Running the Application

```bash
# Start the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser and navigate to: **http://localhost:8000**

## 📖 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload a single PDF file |
| `POST` | `/upload-multiple` | Upload multiple PDF files |
| `GET` | `/results/{job_id}` | Get processing results |
| `GET` | `/export/{job_id}?format=csv` | Export results (csv/txt/xlsx) |
| `GET` | `/status` | API health check |
| `DELETE` | `/results/{job_id}` | Delete job results |

### Example Usage

```bash
# Upload a PDF
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf"

# Get results
curl "http://localhost:8000/results/{job_id}"

# Export as CSV
curl "http://localhost:8000/export/{job_id}?format=csv" -o emails.csv
```

### Interactive API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## ⚙️ Configuration

Edit `backend/config.py` to customize:

```python
# File settings
MAX_FILE_SIZE_MB = 20
AUTO_DELETE_AFTER_SECONDS = 3600

# Validation settings
ENABLE_DNS_LOOKUP = False  # Enable for MX record validation
DNS_TIMEOUT = 5

# Blacklists
EMAIL_BLACKLIST = ["test@test.com", "example@example.com"]
DOMAIN_BLACKLIST = ["localhost", "test.com"]

# Known valid domains (for confidence scoring)
KNOWN_VALID_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com"]
```

## 🧪 Testing

### Test with Sample PDFs

1. Upload a text-based PDF with visible emails
2. Upload a scanned PDF (requires Tesseract)
3. Upload a PDF with obfuscated emails (e.g., `user [at] domain [dot] com`)

### Expected Output

```json
{
  "id": "abc123",
  "status": "completed",
  "total_emails": 15,
  "valid_emails": 12,
  "invalid_emails": 3,
  "emails": [
    {
      "email": "john.doe@gmail.com",
      "confidence": 95.0,
      "is_valid": true,
      "domain": "gmail.com",
      "context": "Contact: John Doe - [EMAIL]",
      "name_hint": "John Doe"
    }
  ],
  "processing_time": 2.5
}
```

## 🔒 Security

- Files are auto-deleted after processing (configurable)
- No permanent storage of uploaded PDFs
- Input sanitization on all uploads
- File type and size validation
- Rate limiting ready (configure in production)

## 📈 Performance Tips

- For large PDFs, processing is asynchronous
- Results are cached for repeated downloads
- OCR is only triggered if text extraction yields minimal content
- DNS lookups are cached (LRU cache)

## 🛠️ Troubleshooting

### Common Issues

1. **OCR not working**
   - Ensure Tesseract is installed and in PATH
   - Check `pytesseract.pytesseract.tesseract_cmd` path

2. **Import errors**
   - Activate the virtual environment
   - Reinstall dependencies: `pip install -r requirements.txt`

3. **File too large error**
   - Increase `MAX_FILE_SIZE_MB` in config.py

4. **DNS lookup timeouts**
   - Set `ENABLE_DNS_LOOKUP = False` in config.py

## 🔮 Future Enhancements

- [ ] Bulk upload (ZIP files)
- [ ] Email domain analytics dashboard
- [ ] CRM integration (HubSpot, Salesforce)
- [ ] Chrome extension
- [ ] AI-based entity recognition (NER)
- [ ] PostgreSQL/Redis for production

## 📄 License

MIT License - feel free to use and modify for your projects.

---

Built with ❤️ using FastAPI and modern JavaScript
