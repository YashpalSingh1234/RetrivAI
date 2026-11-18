from backend.app.ingestion.loaders import load_pdf
from backend.app.ingestion.cleaner import clean_text, clean_document


#step 1: load pdf
document = load_pdf(r"testdata\Big_Data_Basics_Complete_Study_Notes.pdf")

#step 2: clean document
cleaned_document = clean_document(document)

# step3: check result

print("filename", cleaned_document["filename"])
print("Total Pages:", cleaned_document["total_page"])

print("\nCleaned text:")
print("Total pages:", cleaned_document['text'][:1000])

print("\nPage 1:")
print(cleaned_document["pages"][0]["text"][:500])