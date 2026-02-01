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
                        # Render page to image with high resolution for better OCR
                        # Using 4x zoom (equivalent to ~288 DPI) for better text recognition
                        pix = page.get_pixmap(matrix=self.fitz.Matrix(4, 4))
                        img_data = pix.tobytes("png")
                        
                        # OCR the image with preprocessing
                        image = self.Image.open(io.BytesIO(img_data))
                        page_text = self._ocr_with_preprocessing(image)
                        
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
                    images = convert_from_path(pdf_path, dpi=400)  # Higher DPI for better OCR
                    for i, image in enumerate(images, 1):
                        page_text = self._ocr_with_preprocessing(image)
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
    
    def _ocr_with_preprocessing(self, image) -> str:
        """
        Apply image preprocessing and OCR with multiple strategies for better accuracy.
        """
        import cv2
        import numpy as np
        
        # Convert PIL Image to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        all_text_parts = []
        
        # Strategy 1: Adaptive thresholding (good for varied lighting)
        try:
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            pil_img = self.Image.fromarray(adaptive)
            text1 = self.pytesseract.image_to_string(
                pil_img, 
                lang=self.ocr_language,
                config='--psm 6 --oem 3'
            )
            all_text_parts.append(text1)
        except Exception as e:
            logger.debug(f"Adaptive threshold OCR failed: {e}")
        
        # Strategy 2: Simple binary threshold with OTSU
        try:
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            pil_img = self.Image.fromarray(otsu)
            text2 = self.pytesseract.image_to_string(
                pil_img, 
                lang=self.ocr_language,
                config='--psm 6 --oem 3'
            )
            all_text_parts.append(text2)
        except Exception as e:
            logger.debug(f"OTSU threshold OCR failed: {e}")
        
        # Strategy 3: Contrast enhancement + denoising
        try:
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            pil_img = self.Image.fromarray(denoised)
            text3 = self.pytesseract.image_to_string(
                pil_img, 
                lang=self.ocr_language,
                config='--psm 4 --oem 3'  # PSM 4: single column of variable sizes
            )
            all_text_parts.append(text3)
        except Exception as e:
            logger.debug(f"Enhanced OCR failed: {e}")
        
        # Strategy 4: Original image with different PSM
        try:
            text4 = self.pytesseract.image_to_string(
                image, 
                lang=self.ocr_language,
                config='--psm 3 --oem 3'  # PSM 3: fully automatic page segmentation
            )
            all_text_parts.append(text4)
        except Exception as e:
            logger.debug(f"Original image OCR failed: {e}")
        
        # Combine all extracted texts and extract unique emails
        # Use regex to find all email patterns from all strategies
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        all_emails = set()
        combined_text = "\n".join(all_text_parts)
        
        # Find all emails from all strategies
        for text in all_text_parts:
            emails = re.findall(email_pattern, text)
            all_emails.update(emails)
        
        # Return the combined text plus a summary of found emails
        # This ensures we capture emails even if they appear in only one strategy
        if all_emails:
            email_section = "\n--- Extracted Emails ---\n" + "\n".join(all_emails)
            return combined_text + email_section
        
        return combined_text
    
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
