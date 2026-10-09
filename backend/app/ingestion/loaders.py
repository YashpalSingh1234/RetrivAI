from pathlib import Path


import pymupdf


def load_pdf(file_path:str) -> dict:
    """
    Extract text form a pdf page by page
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError()

    if not path.isfile():
        raise ValueError("Provided path is not a file")

    if path.suffix.lower() != "pdf":
        raise ValueError("Only pdf file are asupported")


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

    except