import fitz
import sys

def extract_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    
    with open("pdf_contents.txt", "w", encoding="utf-8") as f:
        f.write(text)

if __name__ == "__main__":
    extract_pdf("ppt_cad.pdf")
