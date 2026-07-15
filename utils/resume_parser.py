import tempfile
import hashlib
from pathlib import Path

from docx import Document
import pdfplumber


def read_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def read_pdf(path: str) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def parse_resume(uploaded_file) -> tuple[str, str]:
    """Yüklenen dosyayı okur, (metin, içerik_hash) döner.

    Desteklenen formatlar: .docx, .pdf
    İçerik hash'i dosya adı yerine dedup için kullanılır.
    """
    suffix = Path(uploaded_file.name).suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    if suffix == ".docx":
        text = read_docx(tmp_path)
    elif suffix == ".pdf":
        text = read_pdf(tmp_path)
    else:
        raise ValueError(f"Desteklenmeyen format: {suffix}")

    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return text, content_hash
