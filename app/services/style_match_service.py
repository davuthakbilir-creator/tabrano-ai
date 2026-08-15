from openai import OpenAI
from dotenv import load_dotenv
import os
import json


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30.0)


STYLE_MATCH_PROMPT_TEMPLATE = """
Kullanıcı şu stili arıyor: "{style_request}"

Aşağıda, önceden görsel analizle çıkarılmış stil profilleri olan
aday ürünler var. Her ürünün stiline, formuna, ruh haline ve
anahtar kelimelerine bakarak, kullanıcının istediği stille en
UYUMLU olan ürünleri en uyumludan en az uyumluya sırala.

Ürünler:
{products_text}

SADECE şu formatta bir JSON döndür:
{{"ranked_ids": [en_uyumlu_id, ..., en_az_uyumlu_id]}}

Sadece gerçekten makul ölçüde uyumlu olanları dahil et, hiç
uyumsuz olanları listeden çıkarabilirsin. Başka metin ekleme.
"""


def strip_code_fence(text):

    text = text.strip()

    if text.startswith("```"):

        text = text.strip("`")

        if text.lower().startswith("json"):

            text = text[4:].strip()

    return text


def rank_products_by_style(style_request, candidate_products):

    scored = [
        p for p in candidate_products
        if p.get("style_profile")
    ]

    if not scored:

        return candidate_products


    products_text = ""

    for p in scored:

        profile = p["style_profile"]

        products_text += f"""
id: {p['id']}
ad: {p['name']}
stil_etiketleri: {profile.get('style_tags', [])}
form: {profile.get('form', '')}
ruh_hali: {profile.get('mood', '')}
anahtar_kelimeler: {profile.get('keywords', [])}
"""

    prompt = STYLE_MATCH_PROMPT_TEMPLATE.format(
        style_request=style_request,
        products_text=products_text
    )

    try:

        response = client.responses.create(
            model="gpt-5.5",
            input=[{"role": "user", "content": prompt}]
        )

    except Exception as e:

        print("STYLE MATCH: OpenAI HATASI:", repr(e))

        return candidate_products

    text = strip_code_fence(response.output_text)

    try:

        result = json.loads(text)

    except json.JSONDecodeError as e:

        print("STYLE MATCH: JSON PARSE HATASI:", e, "RAW:", text)

        return candidate_products

    ranked_ids = result.get("ranked_ids", [])

    by_id = {p["id"]: p for p in candidate_products}

    ranked = [by_id[i] for i in ranked_ids if i in by_id]

    # Sıralanmayan (modelin elemediği/atladığı) ürünleri sona ekle
    remaining = [p for p in candidate_products if p["id"] not in ranked_ids]

    return ranked + remaining