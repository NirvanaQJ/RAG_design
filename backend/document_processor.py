import os
import uuid
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
import pdfplumber

from config import settings


def extract_text_from_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_pdf(file_path: str) -> str:
    text_parts = []
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    except Exception:
        pass

    if not text_parts:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception:
            pass

    return "\n".join(text_parts)


def extract_text_from_image(file_path: str) -> str:
    try:
        import easyocr
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        result = reader.readtext(file_path)

        text_lines = []
        for detection in result:
            text = detection[1]
            text_lines.append(text)

        return "\n".join(text_lines)
    except ImportError:
        return "[OCR引擎未安装，请安装easyocr]"


def extract_text(file_path: str, file_type: str) -> str:
    ext = file_type.lower()
    if ext in ("docx", "doc"):
        return extract_text_from_docx(file_path)
    elif ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext in ("png", "jpg", "jpeg", "bmp", "tiff", "gif"):
        return extract_text_from_image(file_path)
    elif ext == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"不支持的文件格式: {file_type}")


def split_text_into_chunks(text: str) -> List[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
    )
    chunks = text_splitter.split_text(text)
    return chunks


def save_upload_file(file_content: bytes, original_filename: str) -> tuple:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "unknown"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path, ext
