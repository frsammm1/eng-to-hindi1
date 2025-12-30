import fitz # PyMuPDF

def extract_and_store(pdf_path, file_id):
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc):
        blocks = page.get_text("blocks")
        for b in blocks:
            # b = (x0, y0, x1, y1, "text", block_no, block_type)
            text = b[4].strip()
            if text:
                save_block(file_id, page_num, text, list(b[:4]), "content")

def rebuild_pdf(file_id, original_pdf, output_pdf):
    doc = fitz.open(original_pdf)
    font_path = "hindi_font.ttf" # Repo mein ye file honi chahiye
    
    tasks = db.translation_tasks.find({"file_id": file_id, "status": "completed"})
    
    for task in tasks:
        page = doc[task['page_num']]
        rect = task['bbox']
        
        # 1. Purana English mitao (White Box)
        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 2. Hindi likho
        page.insert_text(rect[:2], task['translated_text'], 
                         fontname="hindi", fontfile=font_path, fontsize=8)
    
    doc.save(output_pdf)
  
