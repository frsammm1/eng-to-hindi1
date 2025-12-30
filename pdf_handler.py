import fitz
import logging
from database import save_block, get_recent_completed, get_all_completed

def extract_and_store(pdf_path, file_id):
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc):
            blocks = page.get_text("blocks")
            for b in blocks:
                text = b[4].strip()
                if text:
                    save_block(file_id, page_num, text, list(b[:4]))
        doc.close()
    except Exception as e:
        logging.error(f"Error extracting PDF: {e}")

def create_mini_pdf(file_id, output_path, batch_size=100):
    try:
        doc = fitz.open()
        page = doc.new_page()
        font_path = "hindi_font.ttf"

        tasks = get_recent_completed(file_id, batch_size)
        if not tasks:
            return None

        y_offset = 50

        for task in tasks:
            if y_offset > 750:
                page = doc.new_page()
                y_offset = 50
            text = f"Q: {task['translated_text']}\n"
            try:
                page.insert_text((50, y_offset), text, fontname="hindi", fontfile=font_path, fontsize=9)
            except:
                # Fallback if font issues
                page.insert_text((50, y_offset), text, fontsize=9)
            y_offset += 40

        doc.save(output_path)
        doc.close()
        return output_path
    except Exception as e:
        logging.error(f"Error creating mini PDF: {e}")
        return None

def rebuild_final_pdf(file_id, original_pdf, output_pdf):
    try:
        doc = fitz.open(original_pdf)
        font_path = "hindi_font.ttf"
        
        tasks = get_all_completed(file_id)
        
        for task in tasks:
            try:
                if task['page_num'] < len(doc):
                    page = doc[task['page_num']]
                    rect = task['bbox']

                    # Redact English
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    page.apply_redactions()

                    # Dynamic Scaling Logic
                    text = task['translated_text']
                    if text:
                        fsize = 8
                        text_width = fitz.get_text_length(text, fontsize=fsize)
                        if text_width > (rect[2] - rect[0]): fsize = 6 # Font chota karo agar fit na ho

                        try:
                            page.insert_text(rect[:2], text, fontname="hindi", fontfile=font_path, fontsize=fsize)
                        except:
                            page.insert_text(rect[:2], text, fontsize=fsize)
            except Exception as e:
                logging.error(f"Error processing task on page {task.get('page_num')}: {e}")
                continue
        
        doc.save(output_pdf)
        doc.close()
        return output_pdf
    except Exception as e:
        logging.error(f"Error rebuilding final PDF: {e}")
        return None
