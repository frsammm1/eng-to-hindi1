import fitz

def extract_and_store(pdf_path, file_id):
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc):
        blocks = page.get_text("blocks")
        for b in blocks:
            text = b[4].strip()
            if text:
                from database import save_block
                save_block(file_id, page_num, text, list(b[:4]))

def create_mini_pdf(file_id, output_path):
    from database import get_recent_completed
    doc = fitz.open()
    page = doc.new_page()
    font_path = "hindi_font.ttf"
    
    tasks = get_recent_completed(file_id, 100)
    y_offset = 50
    
    for task in tasks:
        if y_offset > 750:
            page = doc.new_page()
            y_offset = 50
        text = f"Q: {task['translated_text']}\n"
        page.insert_text((50, y_offset), text, fontname="hindi", fontfile=font_path, fontsize=9)
        y_offset += 40
    
    doc.save(output_path)

def rebuild_final_pdf(file_id, original_pdf, output_pdf):
    from database import db
    doc = fitz.open(original_pdf)
    font_path = "hindi_font.ttf"
    
    tasks = db.translation_tasks.find({"file_id": file_id, "status": "completed"})
    
    for task in tasks:
        page = doc[task['page_num']]
        rect = task['bbox']
        
        # Redact English
        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # Dynamic Scaling Logic
        text = task['translated_text']
        fsize = 8
        text_width = fitz.get_text_length(text, fontsize=fsize)
        if text_width > (rect[2] - rect[0]): fsize = 6 # Font chota karo agar fit na ho
        
        page.insert_text(rect[:2], text, fontname="hindi", fontfile=font_path, fontsize=fsize)
    
    doc.save(output_pdf)
    
