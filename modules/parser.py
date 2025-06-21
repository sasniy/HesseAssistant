# modules/parser.py
import fitz  # PyMuPDF
from ebooklib import epub
from bs4 import BeautifulSoup

import chardet

def extract_text_from_txt(file):
    raw = file.read()
    result = chardet.detect(raw)
    encoding = result['encoding'] or 'utf-8'  # fallback
    return raw.decode(encoding, errors='ignore')


def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_epub(file):
    book = epub.read_epub(file)
    text = ''
    for item in book.get_items():
        if item.get_type() == 9:  # DOCUMENT
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text += soup.get_text()
    return text

def extract_text(file, filename):
    text = ""
    title = "Неизвестно"
    author = "Неизвестен"

    if filename.endswith(".txt"):
        raw = file.read()
        result = chardet.detect(raw)
        encoding = result['encoding'] or 'utf-8'
        text = raw.decode(encoding, errors='ignore')
        # Попробуем найти что-то в первых строках
        lines = text.splitlines()
        for line in lines[:10]:
            if "автор" in line.lower():
                author = line.strip()
            if "название" in line.lower() or "title" in line.lower():
                title = line.strip()

    elif filename.endswith(".pdf"):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        # попытаемся достать метаданные
        meta = doc.metadata
        title = meta.get("title") or "Неизвестно"
        author = meta.get("author") or "Неизвестен"

    elif filename.endswith(".epub"):
        book = epub.read_epub(file)
        text = ''
        title = book.get_metadata('DC', 'title')
        author = book.get_metadata('DC', 'creator')
        title = title[0][0] if title else "Неизвестно"
        author = author[0][0] if author else "Неизвестен"
        for item in book.get_items():
            if item.get_type() == 9:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text += soup.get_text()
    else:
        return "Unsupported format", "", ""

    return text, title, author
