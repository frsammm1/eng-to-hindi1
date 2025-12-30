import os
import asyncio
from pyrogram import Client, filters
from pdf_handler import extract_and_store, rebuild_pdf
from database import get_next_batch, update_task
from translator import translate_with_retry

app = Client(
    "ssc_heavy_bot",
    api_id=os.getenv("API_ID"),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

@app.on_message(filters.document & filters.private)
async def start_translation(client, message):
    file_id = message.document.file_unique_id
    doc_path = await message.download()
    
    await message.reply("Analysis shuru... Saare blocks MongoDB mein save ho rahe hain.")
    extract_and_store(doc_path, file_id)
    
    await message.reply("Translation shuru ho gayi hai. Har 100 questions par update milega.")
    
    # Background Processing Loop
    processed_count = 0
    while True:
        batch = get_next_batch(file_id)
        if not batch: break
        
        for task in batch:
            hindi_text = translate_with_retry(task['original_text'])
            if hindi_text:
                update_task(task['_id'], hindi_text)
                processed_count += 1
            
            if processed_count % 100 == 0:
                await message.reply(f"✅ {processed_count} blocks processed...")
                
        await asyncio.sleep(2) # Flood avoidance

    await message.reply("Final PDF generate ho rahi hai...")
    output_name = f"Hindi_{message.document.file_name}"
    rebuild_pdf(file_id, doc_path, output_name)
    await message.reply_document(output_name)

if __name__ == "__main__":
    app.run()
  
