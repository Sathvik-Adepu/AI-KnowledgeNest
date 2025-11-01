import os
import fitz  # PyMuPDF
import docx

def extract_text_from_txt(file):
    return file.read().decode('utf-8')

def extract_text_from_pdf(file):
    text = ""
    pdf_doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf_doc:
        text += page.get_text()
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    paras = [para.text for para in doc.paragraphs if para.text.strip() != ""]
    return "\n".join(paras)

def extract_text_from_file(file_storage):
    filename = file_storage.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_storage)
    elif ext == '.docx':
        return extract_text_from_docx(file_storage)
    elif ext == '.txt':
        return extract_text_from_txt(file_storage)
    else:
        return ""
