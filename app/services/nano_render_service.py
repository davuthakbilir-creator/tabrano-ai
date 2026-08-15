from google import genai
from google.genai.types import GenerateContentConfig, Modality
from PIL import Image
from io import BytesIO
import requests
import base64
from dotenv import load_dotenv
import os
from collections import defaultdict
from datetime import date


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


NANO_MODEL = "gemini-2.5-flash-image"


RENDER_DAILY_LIMIT = 50

_usage_counter = defaultdict(lambda: defaultdict(int))


def check_and_increment_usage(client_id: str):

    today = date.today().isoformat()

    count = _usage_counter[client_id][today]

    if count >= RENDER_DAILY_LIMIT:

        return False, count

    _usage_counter[client_id][today] = count + 1

    return True, count + 1


def download_image_bytes(url: str) -> bytes:

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    return response.content


def resolve_image_bytes(source) -> bytes:

    if isinstance(source, bytes):

        return source

    if isinstance(source, str):

        if source.startswith("http://") or source.startswith("https://"):

            return download_image_bytes(source)

        if source.startswith("data:"):

            source = source.split(",", 1)[1]

        return base64.b64decode(source)

    raise ValueError("Desteklenmeyen görsel formatı")


# -----------------------------------------------------
# MOD 2: ODANDA GÖR (kullanıcının gerçek oda fotoğrafı var)
# -----------------------------------------------------

ROOM_PREVIEW_PROMPT_TEMPLATE = """
The furniture in the second image ("{product_name}") is an exact
commercial product sold by a real furniture retailer.

Preserve the product exactly. Do not redesign, recreate or generate
a similar furniture. Keep the original shape, legs, dimensions,
materials and colors of the product completely unchanged.

IMPORTANT — REPLACING EXISTING FURNITURE:
If the room in the first image already contains a piece of furniture
of the same type/category as this product (for example, if this
product is a table and the room already has a table, or this product
is a console and the room already has a console), REMOVE that
existing piece of furniture completely and place this exact product
in its place instead. Do NOT show both the old and the new furniture
together — the goal is to visualize the room as it would look WITH
this new product replacing the old one, not alongside it.

If the room does not already contain a similar piece of furniture,
simply add this product into a sensible empty area of the room.

Only adjust:
- perspective, to match the room's camera angle
- lighting and shadows, to match the room's light sources
- scale, so the product looks proportionally correct in the room

Do not change anything else about the room (walls, floor, other
different types of furniture, decor).
"""


def generate_room_render(
    room_image_bytes: bytes,
    room_content_type: str,
    product_image_url: str,
    product_name: str,
    client_id: str
):

    allowed, usage_count = check_and_increment_usage(
        client_id
    )

    if not allowed:

        return {
            "image_base64": None,
            "error": (
                "Günlük render limitine ulaştınız "
                f"({RENDER_DAILY_LIMIT}/gün). Lütfen yarın "
                "tekrar deneyin."
            )
        }

    if not GEMINI_API_KEY:

        return {
            "image_base64": None,
            "error": (
                "GEMINI_API_KEY tanımlı değil. "
                ".env dosyasına GEMINI_API_KEY ekleyin."
            )
        }

    try:

        product_bytes = resolve_image_bytes(product_image_url)

        room_bytes = resolve_image_bytes(room_image_bytes)

    except Exception as e:

        print("NANO RENDER: GÖRSEL ÇÖZÜMLEME HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Görseller okunamadı."
        }

    try:

        product_pil = Image.open(BytesIO(product_bytes)).convert("RGB")

        room_pil = Image.open(BytesIO(room_bytes)).convert("RGB")

    except Exception as e:

        print("NANO RENDER: GÖRSEL AÇMA HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Görseller açılamadı."
        }

    prompt = ROOM_PREVIEW_PROMPT_TEMPLATE.format(product_name=product_name)

    print("NANO RENDER (room_preview): Gemini'a istek gönderiliyor...")

    try:

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=NANO_MODEL,
            contents=[room_pil, product_pil, prompt],
            config=GenerateContentConfig(
                response_modalities=[Modality.TEXT, Modality.IMAGE]
            )
        )

    except Exception as e:

        print("NANO RENDER: GEMINI ÇAĞRISI HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Render oluşturulurken bir hata oluştu."
        }

    print("NANO RENDER (room_preview): Gemini'dan cevap geldi")

    result_bytes = None

    try:

        for part in response.candidates[0].content.parts:

            if part.inline_data:

                result_bytes = part.inline_data.data

                break

    except Exception as e:

        print("NANO RENDER: CEVAP PARSE HATASI:", repr(e))

    if not result_bytes:

        return {
            "image_base64": None,
            "error": "Model bir görsel döndürmedi."
        }

    image_b64 = base64.b64encode(result_bytes).decode("utf-8")

    return {
        "image_base64": image_b64,
        "error": None,
        "usage_count": usage_count,
        "usage_limit": RENDER_DAILY_LIMIT
    }


# -----------------------------------------------------
# MOD 1: AI TASARIM (oda fotoğrafı yok — model yeni bir
# ortam üretir, ürünü o ortama yerleştirir)
# -----------------------------------------------------

AI_DESIGN_PROMPT_TEMPLATE = """
The furniture in the reference image ("{product_name}") is an exact
commercial product sold by a real furniture retailer.

Preserve the product exactly. Do not redesign, recreate, or generate
a different furniture piece. Keep the original shape, legs,
dimensions, materials and colors of the product completely unchanged.

IMPORTANT — ENVIRONMENT MUST MATCH THE PRODUCT'S NATURAL SETTING:
Look at what kind of product this is. If it is outdoor/garden/patio
furniture (e.g. garden sets, patio chairs, outdoor tables/umbrellas),
you MUST place it in a realistic OUTDOOR setting (a garden, patio,
balcony, or terrace) — never inside a closed living room or indoor
space. If it is indoor furniture, place it in a realistic indoor
room appropriate to its type (living room, dining room, bedroom,
etc.) — never outdoors.

Generate a brand new, photorealistic scene around this exact
product, based on this style description from the customer:
"{style}"

The scene should look like a real, tastefully designed space (not a
studio product shot) with realistic lighting, shadows, and
complementary decor appropriate to the setting — but the furniture
piece itself must remain completely unchanged and clearly
recognizable as the exact same product shown in the reference image.
"""


def generate_ai_design(
    product_image,
    style: str,
    product_name: str = "ürün",
    client_id: str = "anonymous"
):

    allowed, usage_count = check_and_increment_usage(
        client_id
    )

    if not allowed:

        return {
            "image_base64": None,
            "error": (
                "Günlük render limitine ulaştınız "
                f"({RENDER_DAILY_LIMIT}/gün). Lütfen yarın "
                "tekrar deneyin."
            )
        }

    if not GEMINI_API_KEY:

        return {
            "image_base64": None,
            "error": (
                "GEMINI_API_KEY tanımlı değil. "
                ".env dosyasına GEMINI_API_KEY ekleyin."
            )
        }

    try:

        product_bytes = resolve_image_bytes(product_image)

    except Exception as e:

        print("NANO AI DESIGN: GÖRSEL ÇÖZÜMLEME HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Ürün görseli okunamadı."
        }

    try:

        product_pil = Image.open(BytesIO(product_bytes)).convert("RGB")

    except Exception as e:

        print("NANO AI DESIGN: GÖRSEL AÇMA HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Ürün görseli açılamadı."
        }

    style_text = (
        style.strip()
        if style and style.strip()
        else "modern, sıcak ve davetkar bir yaşam alanı"
    )

    prompt = AI_DESIGN_PROMPT_TEMPLATE.format(
        product_name=product_name,
        style=style_text
    )

    print("NANO AI DESIGN: Gemini'a istek gönderiliyor... stil:", style_text)

    try:

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=NANO_MODEL,
            contents=[product_pil, prompt],
            config=GenerateContentConfig(
                response_modalities=[Modality.TEXT, Modality.IMAGE]
            )
        )

    except Exception as e:

        print("NANO AI DESIGN: GEMINI ÇAĞRISI HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Render oluşturulurken bir hata oluştu."
        }

    print("NANO AI DESIGN: Gemini'dan cevap geldi")

    result_bytes = None

    try:

        for part in response.candidates[0].content.parts:

            if part.inline_data:

                result_bytes = part.inline_data.data

                break

    except Exception as e:

        print("NANO AI DESIGN: CEVAP PARSE HATASI:", repr(e))

    if not result_bytes:

        return {
            "image_base64": None,
            "error": "Model bir görsel döndürmedi."
        }

    image_b64 = base64.b64encode(result_bytes).decode("utf-8")

    return {
        "image_base64": image_b64,
        "error": None,
        "usage_count": usage_count,
        "usage_limit": RENDER_DAILY_LIMIT
    }