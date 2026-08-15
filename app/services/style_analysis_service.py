from openai import OpenAI
from dotenv import load_dotenv
import os
import json


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=60.0
)


STYLE_ANALYSIS_PROMPT = """
Sen bir iç mimarsın. Sana bir mobilya ürününün fotoğrafı ve
metin bilgileri verilecek.

Ürün fotoğrafını, geometrik formunu, renklerini, malzemesini ve
açıklamasını analiz ederek, bu ürünün hangi iç mimari stillerine
uygun olduğunu SEN çıkar — ürüne önceden verilmiş bir stil etiketi
YOKTUR, bunu tamamen görsel ve metinsel analizden çıkarman gerekiyor.

SADECE aşağıdaki alanları içeren bir JSON döndür:

- style_tags: bu ürünün uyduğu 2-4 iç mimari stili, liste olarak
  (örn. ["Modern", "Minimalist"], ["Japandi", "Doğal"], ["Klasik", "Lüks"])
- form: ürünün geometrik formunun kısa tanımı (örn. "keskin köşeli,
  düz hatlı", "yuvarlak, organik", "asimetrik")
- mood: ürünün genel hissi/ruh hali (örn. "sıcak ve davetkar",
  "soğuk ve minimal", "gösterişli ve lüks")
- keywords: bu ürünü tarif eden 5-8 serbest anahtar kelime, liste
  olarak (örn. ["ahşap", "doğal doku", "sade", "geniş", "alçak profil"])

Sadece JSON döndür, başka hiçbir metin ekleme, kod bloğu kullanma.
"""


def strip_code_fence(text):

    text = text.strip()

    if text.startswith("```"):

        text = text.strip("`")

        if text.lower().startswith("json"):

            text = text[4:].strip()

    return text


def analyze_product_style(name, description, color, material, image_url):

    if not image_url:

        return None

    context_text = f"""
Ürün adı: {name}
Renk: {color or "belirtilmemiş"}
Malzeme: {material or "belirtilmemiş"}
Açıklama: {(description or "")[:600]}
"""

    try:

        response = client.responses.create(
            model="gpt-5.5",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": STYLE_ANALYSIS_PROMPT + context_text},
                        {"type": "input_image", "image_url": image_url},
                    ]
                }
            ]
        )

    except Exception as e:

        print("STYLE ANALYSIS: OpenAI HATASI:", repr(e))

        return None

    text = strip_code_fence(response.output_text)

    try:

        return json.loads(text)

    except json.JSONDecodeError as e:

        print("STYLE ANALYSIS: JSON PARSE HATASI:", e, "RAW:", text)

        return None