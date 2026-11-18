import re
import unicodedata

def clean_text(text: str) -> str:
    """
    Clean extracted PDF text without removing
    important semantic information.
    """


    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    if not text.strip():
        return ""

    # 1. Normalize Unicode charcters

    text = unicodedata.normalize("NFC", text)

    # 2. Normalize different line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # 3. Remove invisible control characters 
    # Preserve newline and tab temporarily

    text = "".join(
        char for char in text
        if char in("\n", "\t")
        or unicodedata.category(char) != "Cc"
    )

    # 4. Normalize horizontal whitespace

    text = re.sub(r"[^\S\n]+", " ", text)

    #5. Remove spaces around line breaks

    text = re.sub(r" *\n *", "\n", text)

    # 6. Remove excessive empty lines

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()



def clean_document(document:dict) -> dict:
    """
    Clean every PDF page while preserving
    filename and page metadata.
    """

    cleaned_pages = []

    for page in document["pages"]:
        cleaned_pages.append({
            **page,
            "text":clean_text(page["text"])
        })

    full_text = "\n\n".join(
        page["text"]
        for page in cleaned_pages
        if page["text"]
    )


    return{
        **document,
        "text":full_text,
        "pages": cleaned_pages
    }