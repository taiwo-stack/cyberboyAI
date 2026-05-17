import os
from openai import AsyncOpenAI

async def extract_text_from_image(base64_image: str) -> str:
    """
    Uses OpenAI Vision to extract text and URLs from a user-uploaded screenshot.
    Returns the extracted raw text.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""
        
    try:
        client = AsyncOpenAI(api_key=api_key)
        
        # Ensure the base64 string is properly formatted for OpenAI
        # If it doesn't have the data URL prefix, add a generic one
        if not base64_image.startswith("data:image"):
            base64_image = f"data:image/jpeg;base64,{base64_image}"
            
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all the text from this image exactly as written. If there is a QR code in the image, decode its contents and include the URL it points to. Pay special attention to extracting any URLs, links, or email addresses perfectly. Do not add any conversational filler, just return the raw extracted text."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": base64_image
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        extracted_text = response.choices[0].message.content.strip()
        print(f"[VisionTool] Extracted text length: {len(extracted_text)}")
        return extracted_text
        
    except Exception as e:
        print(f"[VisionTool] Error extracting text from image: {e}")
        return ""
