import fitz
import logging
from database import save_block, get_all_completed_tasks

def extract_and_store(pdf_path, file_id):
    """
    Extracts text blocks from PDF and saves them to DB.
    """
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc):
            blocks = page.get_text("blocks")
            for b in blocks:
                # b format: (x0, y0, x1, y1, text, block_no, block_type)
                text = b[4].strip()
                if text:
                    save_block(file_id, page_num, text, list(b[:4]))
        doc.close()
        return True
    except Exception as e:
        logging.error(f"Error extracting PDF: {e}")
        return False

def rebuild_final_pdf(file_id, original_pdf, output_pdf):
    """
    Rebuilds the PDF by overlaying translated text.
    """
    try:
        doc = fitz.open(original_pdf)
        font_path = "hindi_font.ttf"

        tasks = get_all_completed_tasks(file_id)
        if not tasks:
            logging.warning("No completed tasks found for PDF rebuild.")
            return None

        for task in tasks:
            try:
                page_num = task.get('page_num')
                if page_num is not None and page_num < len(doc):
                    page = doc[page_num]
                    rect = task.get('bbox')
                    text = task.get('translated_text')

                    if not rect or not text:
                        continue

                    # Redact original text
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    page.apply_redactions()

                    # Calculate optimal font size
                    fsize = 9
                    rect_width = rect[2] - rect[0]
                    rect_height = rect[3] - rect[1]

                    # Simple fitting logic
                    text_length = fitz.get_text_length(text, fontsize=fsize, fontname="helv") # approx
                    if text_length > rect_width:
                        fsize = max(6, fsize * (rect_width / text_length))

                    # Insert Hindi Text
                    # Note: complex scripts support in pymupdf is limited, but this is best effort.
                    try:
                        page.insert_text((rect[0], rect[3] - 2), text, fontname="hindi", fontfile=font_path, fontsize=fsize, color=(0, 0, 0))
                    except Exception as font_err:
                        # Fallback
                         page.insert_text((rect[0], rect[3] - 2), text, fontsize=fsize, color=(0, 0, 0))

            except Exception as e:
                logging.error(f"Error processing task on page {task.get('page_num')}: {e}")
                continue
        
        doc.save(output_pdf)
        doc.close()
        return output_pdf
    except Exception as e:
        logging.error(f"Error rebuilding final PDF: {e}")
        return None
