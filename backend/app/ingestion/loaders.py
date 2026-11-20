from io import BytesIO
from pathlib import Path

import pymupdf


def load_pdf(file_path:str) -> dict:
    """
    Extract text form a pdf page by page
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError()

    if not path.is_file():
        raise ValueError("Provided path is not a file")
    
    if path.suffix.lower() != ".pdf":
        raise ValueError("Only pdf file are supported")


    pages= []
    full_txt = []

    try:
        with pymupdf.open(path) as pdf:
            if pdf.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported")

            if len(pdf) == 0:
                raise ValueError("PDF contains no pages")

            for page_number, page in enumerate(pdf, start=1):
                 text = page.get_text("text").strip()


                 pages.append({
                     "page_number" : page_number,
                     "text" : text
                 })

                 if text:
                     full_txt.append(text)

    except (FileNotFoundError, ValueError):
        raise

    except Exception as exc:
        raise RuntimeError("Failed to read the pdf.") from exc


    return {
        "filename" : path.name,
        "total_page" : len(pages),
        "text" : "\n\n".join(full_txt),
        "pages" : pages,
    }


def load_document_bytes(content: bytes, filename: str) -> dict:
    """Extract a supported PDF, DOCX, or UTF-8 text file into page records."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            pages = []
            with pymupdf.open(stream=content, filetype="pdf") as pdf:
                if pdf.is_encrypted:
                    raise ValueError("Encrypted PDFs are not supported")
                if not len(pdf):
                    raise ValueError("PDF contains no pages")
                for page_number, page in enumerate(pdf, start=1):
                    pages.append({
                        "page_number": page_number,
                        "text": page.get_text("text").strip(),
                    })
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Failed to read the PDF.") from exc
    elif suffix == ".docx":
        try:
            from docx import Document

            doc = Document(BytesIO(content))
            # python-docx exposes paragraphs and tables, but not rendered page
            # boundaries; retain all content under page 1 until a layout engine is used.
            paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        paragraphs.append(" | ".join(cells))
            pages = [{"page_number": 1, "text": "\n".join(paragraphs)}]
        except Exception as exc:
            raise ValueError("Failed to read the DOCX document.") from exc
    elif suffix == ".txt":
        try:
            text = content.decode("utf-8-sig")
            text_pages = text.split("\f")
            pages = [
                {"page_number": index, "text": page.strip()}
                for index, page in enumerate(text_pages, start=1)
            ]
        except UnicodeDecodeError as exc:
            raise ValueError("TXT files must use UTF-8 encoding.") from exc
    else:
        raise ValueError("Only PDF, DOCX, and TXT files are supported.")

    full_text = "\n\n".join(page["text"] for page in pages if page["text"])
    if not full_text.strip():
        raise ValueError("No readable text was found in this document.")
    return {
        "filename": Path(filename).name,
        "total_page": len(pages),
        "text": full_text,
        "pages": pages,
    }
