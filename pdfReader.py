from pypdf import PdfReader

def read_cv(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text

cv_text = read_cv(r"C:\Users\BPSH147\Downloads\samplePdf1.pdf")
print(cv_text)

