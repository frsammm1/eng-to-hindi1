import os
import time
from groq import Groq

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def translate_with_retry(text):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an SSC GS Expert. Translate the following English text to Hindi. Preserve technical terms. Output ONLY the translated text."},
                {"role": "user", "content": text}
            ],
            model="llama3-70b-8192",
            temperature=0.2,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        if "429" in str(e): # Rate Limit
            time.sleep(60)
            return translate_with_retry(text)
        return None
        
