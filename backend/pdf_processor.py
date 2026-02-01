"""
PDF Processor Module
Handles text extraction from PDF files, including OCR for scanned documents.
"""
import logging
from pathlib import Path
from typing import Optional
import io

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Extract text content from PDF files.
    Supports both text-based and scanned/image-based PDFs.
    """
    
    def __init__(self, enable_ocr: bool = True, ocr_language: str = "eng"):
        """
        Initialize PDF processor.
        
        Args:
            enable_ocr: Whether to use OCR for image-based PDFs
            ocr_language: Language code for OCR (default: English)
        """
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if required libraries are available."""
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed. Install with: pip install pdfplumber")
            self.pdfplumber = None
        
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
        except ImportError:
            logger.warning("PyMuPDF not installed. Install with: pip install PyMuPDF")
            self.fitz = None
        
        if self.enable_ocr:
            try:
                import pytesseract
                from PIL import Image
                self.pytesseract = pytesseract
                self.Image = Image
                
                # Configure Tesseract path for Windows
                import platform
                if platform.system() == 'Windows':
                    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    import os
                    if os.path.exists(tesseract_path):
                        pytesseract.pytesseract.tesseract_cmd = tesseract_path
            except ImportError:
                logger.warning("OCR libraries not installed. Install with: pip install pytesseract Pillow")
                self.pytesseract = None
                self.Image = None
    
    def get_page_count(self, pdf_path: str) -> int:
        """Get the number of pages in a PDF."""
        try:
            if self.fitz:
                doc = self.fitz.open(pdf_path)
                count = len(doc)
                doc.close()
                return count
            elif self.pdfplumber:
                with self.pdfplumber.open(pdf_path) as pdf:
                    return len(pdf.pages)
        except:
            pass
        return 0
    
    def extract_text(self, pdf_path: str, progress_callback=None) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            progress_callback: Optional callback function(current_page, total_pages)
            
        Returns:
            Extracted text content
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not path.suffix.lower() == ".pdf":
            raise ValueError(f"Invalid file type: {path.suffix}")
        
        text = ""
        actual_content_length = 0  # Track actual content, not including page markers
        
        # Try pdfplumber first (better for text-based PDFs)
        if self.pdfplumber:
            text, actual_content_length = self._extract_with_pdfplumber(pdf_path, progress_callback)
        
        # If pdfplumber failed or got minimal text, try PyMuPDF
        if actual_content_length < 50 and self.fitz:
            fitz_text, fitz_content_length = self._extract_with_pymupdf(pdf_path, progress_callback)
            if fitz_content_length > actual_content_length:
                text = fitz_text
                actual_content_length = fitz_content_length
        
        # If still minimal text and OCR is enabled, try OCR
        if actual_content_length < 50 and self.enable_ocr and self.pytesseract:
            logger.info("Text extraction minimal, attempting OCR...")
            ocr_text, ocr_content_length = self._extract_with_ocr(pdf_path, progress_callback)
            if ocr_content_length > actual_content_length:
                text = ocr_text
        
        return self._clean_text(text)
    
    def _extract_with_pdfplumber(self, pdf_path: str, progress_callback=None) -> tuple:
        """Extract text using pdfplumber. Returns (text, actual_content_length)."""
        text_parts = []
        actual_content_length = 0
        
        try:
            with self.pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        if progress_callback:
                            progress_callback(page_num, total_pages)
                        
                        page_text = page.extract_text() or ""
                        if page_text:
                            text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                            actual_content_length += len(page_text.strip())
                        
                        # Note: We skip table extraction here because extract_text() 
                        # already includes table content, extracting tables separately
                        # would cause duplicate emails to be counted
                        
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {e}")
                        continue
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
        
        return "\n".join(text_parts), actual_content_length
    
    def _extract_with_pymupdf(self, pdf_path: str, progress_callback=None) -> tuple:
        """Extract text using PyMuPDF (fitz). Returns (text, actual_content_length)."""
        text_parts = []
        actual_content_length = 0
        
        try:
            doc = self.fitz.open(pdf_path)
            total_pages = len(doc)
            for page_num in range(total_pages):
                try:
                    if progress_callback:
                        progress_callback(page_num + 1, total_pages)
                    
                    page = doc.load_page(page_num)
                    page_text = page.get_text("text")
                    if page_text:
                        text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                        actual_content_length += len(page_text.strip())
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num + 1}: {e}")
                    continue
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
        
        return "\n".join(text_parts), actual_content_length
    
    def _extract_with_ocr(self, pdf_path: str, progress_callback=None) -> tuple:
        """Extract text using OCR (for scanned PDFs). Returns (text, actual_content_length)."""
        text_parts = []
        actual_content_length = 0
        
        try:
            if self.fitz:
                doc = self.fitz.open(pdf_path)
                total_pages = len(doc)
                for page_num in range(total_pages):
                    try:
                        if progress_callback:
                            progress_callback(page_num + 1, total_pages)
                        
                        page = doc.load_page(page_num)
                        # Render page to image with higher resolution for better OCR
                        pix = page.get_pixmap(matrix=self.fitz.Matrix(3, 3))  # 3x zoom for better OCR
                        img_data = pix.tobytes("png")
                        
                        # OCR the image
                        image = self.Image.open(io.BytesIO(img_data))
                        page_text = self.pytesseract.image_to_string(
                            image, 
                            lang=self.ocr_language,
                            config='--psm 6'  # Assume uniform block of text
                        )
                        
                        if page_text.strip():
                            text_parts.append(f"--- Page {page_num + 1} (OCR) ---\n{page_text}")
                            actual_content_length += len(page_text.strip())
                    except Exception as e:
                        logger.warning(f"OCR error on page {page_num + 1}: {e}")
                        continue
                doc.close()
            else:
                # Fallback: convert PDF to images using pdf2image if available
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(pdf_path, dpi=300)  # Higher DPI for better OCR
                    for i, image in enumerate(images, 1):
                        page_text = self.pytesseract.image_to_string(
                            image,
                            lang=self.ocr_language,
                            config='--psm 6'
                        )
                        if page_text.strip():
                            text_parts.append(f"--- Page {i} (OCR) ---\n{page_text}")
                            actual_content_length += len(page_text.strip())
                except ImportError:
                    logger.error("pdf2image not installed for OCR fallback")
                    
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
        
        return "\n".join(text_parts), actual_content_length
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Normalize whitespace
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            # Remove excessive whitespace but preserve structure
            line = " ".join(line.split())
            if line:
                cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines)
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """Get metadata about a PDF file."""
        info = {
            "pages": 0,
            "title": None,
            "author": None,
            "encrypted": False,
            "has_images": False
        }
        
        try:
            if self.fitz:
                doc = self.fitz.open(pdf_path)
                info["pages"] = len(doc)
                info["encrypted"] = doc.is_encrypted
                
                metadata = doc.metadata
                if metadata:
                    info["title"] = metadata.get("title")
                    info["author"] = metadata.get("author")
                
                # Check for images
                for page_num in range(min(3, len(doc))):  # Check first 3 pages
                    page = doc.load_page(page_num)
                    if page.get_images():
                        info["has_images"] = True
                        break
                
                doc.close()
                
            elif self.pdfplumber:
                with self.pdfplumber.open(pdf_path) as pdf:
                    info["pages"] = len(pdf.pages)
                    if pdf.metadata:
                        info["title"] = pdf.metadata.get("Title")
                        info["author"] = pdf.metadata.get("Author")
                        
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
        
        return info
