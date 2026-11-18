from backend.app.ingestion.loaders import load_pdf

result = load_pdf(r"testdata\Big_Data_Basics_Complete_Study_Notes.pdf")

print("filename", result['filename'])
print("total_page", result['total_page'])

print("Extracted text:")
print(result["text"][:1000])


print("pages", result['pages'])