import os
from typing import Tuple

import pdfplumber
from flask import current_app


ALLOWED_EXTENSIONS = {"pdf", "txt"}


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _extract_pdf_text(path: str) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_txt_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def save_and_extract_resume(
    file_storage, subdir: str, target_filename: str
) -> Tuple[str, str]:
    """
    Save an uploaded resume file and extract its text.

    Returns (file_path, text). Raises ValueError on validation failure.
    """
    if not file_storage or file_storage.filename == "":
        raise ValueError("No file provided")

    if not allowed_file(file_storage.filename):
        raise ValueError("Only PDF and TXT files are allowed")

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    upload_root = current_app.config["UPLOAD_FOLDER"]
    target_dir = os.path.join(upload_root, subdir)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{target_filename}.{ext}"
    file_path = os.path.join(target_dir, filename)
    file_storage.save(file_path)

    if ext == "pdf":
        text = _extract_pdf_text(file_path)
    else:
        text = _extract_txt_text(file_path)

    if not text:
        raise ValueError("Failed to extract text from file")

    return file_path, text

