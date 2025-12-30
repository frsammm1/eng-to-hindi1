import os
import asyncio
import logging
from pyrogram import Client, filters
from pdf_handler import extract_and_store, rebuild_final_pdf, create_mini_pdf
from database import get_next_batch, update_task, get_completed_count

logging.basicConfig(level=logging.INFO)

app = Client(
    "ssc_heavy_bot",
    api_id=os.getenv("API_ID"),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

@app.on_message(filters.document & filters.private)
async def start_process(client, message):
    file_id = message.document.file_unique_id
    await message.reply("Downloading & Analyzing PDF...")
    doc_path = await message.download()
    
    extract_and_store(doc_path, file_id)
    await message.reply("Analysis Complete. Translation started in background...")

    processed_in_session = 0
    while True:
        batch = get_next_batch(file_id)
        if not batch: break
        
        for task in batch:
            from translator import translate_with_retry
            hindi = translate_with_retry(task['original_text'])
            if hindi:
                update_task(task['_id'], hindi)
                processed_in_session += 1
            
            # Har 100 questions par Mini-PDF
            if processed_in_session % 100 == 0:
                mini_name = f"batch_{processed_in_session}.pdf"
                create_mini_pdf(file_id, mini_name)
                await message.reply_document(mini_name, caption=f"✅ {processed_in_session} questions done!")
        
        await asyncio.sleep(2) # Avoid Flood

    await message.reply("Generating Final Book...")
    final_name = f"HINDI_{message.document.file_name}"
    rebuild_final_pdf(file_id, doc_path, final_name)
    await message.reply_document(final_name, caption="Jai Hind! Poori book Hindi mein tayyar hai.")

if __name__ == "__main__":
    app.run()
    
