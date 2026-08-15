from PIL import Image, ImageFilter, ImageEnhance
import requests
import io
import json
import base64
from collections import defaultdict
from datetime import date

from rembg import remove as remove_background
from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=60.0
)


RENDER_DAILY_LIMIT = 3

_render_usage_counter = defaultdict(lambda: defaultdict(int))


def check_and_increment_render_usage(client_id: str):

    today = date.today().isoformat()

    count = _render_usage_counter[client_id][today]

    if count >= RENDER_DAILY_LIMIT:

        return False, count

    _render_usage_counter[client_id][today] = count + 1

    return True, count + 1


def download_image_bytes(url: str):

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    return response.content


def cutout_product(product_image_bytes: bytes) -> Image.Image:

    result_bytes = remove_background(product_image_bytes)

    cutout = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

    return cutout


# -----------------------------------------------------
# YERLEŞİM ANALİZİ
# -----------------------------------------------------
# OpenAI burada SADECE metin/JSON öneri veriyor — hiçbir görsel
# üretmiyor, ürün görselini hiç görmüyor bile. Sadece oda
# fotoğrafına bakıp "bu tip ürün mantıken nereye, ne büyüklükte
# konur" diye tahmin ediyor.

PLACEMENT_PROMPT_TEMPLATE = """
Sen bir iç mimarsın. Sana bir oda fotoğrafı verilecek.

Odaya "{product_name}" adlı bir mobilya ürünü yerleştirilecek.
Bu ürün büyük ihtimalle bir sehpa, konsol veya masa gibi zemine
konan, orta/küçük boyutlu bir mobilya.

Fotoğrafı analiz et ve SADECE aşağıdaki alanları içeren bir JSON
döndür:

- room_type: oda tipi
- floor_area: ürünün konulabileceği boş zemin alanının kısa açıklaması
- recommended_position: {{"x": 0.0-1.0, "y": 0.0-1.0}} — ürünün SOL
  ÜST köşesinin fotoğraf üzerindeki konumu (0,0 sol üst köşe,
  1,1 sağ alt köşe). Ürün zemine konacağı için y genelde 0.4-0.75
  arası olmalı.
- scale_ratio: 0.0-1.0 arası bir sayı — ürünün genişliğinin, oda
  fotoğrafının genişliğine oranı. Küçük/orta mobilyalar için
  genelde 0.15-0.35 arası mantıklıdır.
- light_direction: odadaki ışığın geldiği yön — "left", "right",
  "top", "top-left", "top-right", "front" değerlerinden biri.

Sadece JSON döndür, başka hiçbir metin ekleme, kod bloğu kullanma.
"""


def strip_code_fence(text):

    text = text.strip()

    if text.startswith("```"):

        text = text.strip("`")

        if text.lower().startswith("json"):

            text = text[4:].strip()

    return text


def analyze_placement(room_image_bytes, room_content_type, product_name):

    b64_image = base64.b64encode(room_image_bytes).decode("utf-8")

    data_url = f"data:{room_content_type};base64,{b64_image}"

    prompt = PLACEMENT_PROMPT_TEMPLATE.format(product_name=product_name)

    print("RENDER: yerleşim analizi için OpenAI'a istek gönderiliyor...")

    try:

        response = client.responses.create(
            model="gpt-5.5",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url},
                    ]
                }
            ]
        )

    except Exception as e:

        print("RENDER: YERLEŞİM ANALİZİ HATASI:", repr(e))

        return None

    text = strip_code_fence(response.output_text)

    try:

        return json.loads(text)

    except json.JSONDecodeError as e:

        print("RENDER: YERLEŞİM JSON PARSE HATASI:", e, "RAW:", text)

        return None


DEFAULT_PLACEMENT = {
    "recommended_position": {"x": 0.35, "y": 0.55},
    "scale_ratio": 0.25,
    "light_direction": "front",
}


def resolve_placement(analysis):

    if not analysis:

        return DEFAULT_PLACEMENT

    position = analysis.get("recommended_position") or {}

    x = position.get("x", DEFAULT_PLACEMENT["recommended_position"]["x"])

    y = position.get("y", DEFAULT_PLACEMENT["recommended_position"]["y"])

    scale_ratio = analysis.get(
        "scale_ratio",
        DEFAULT_PLACEMENT["scale_ratio"]
    )

    light_direction = analysis.get(
        "light_direction",
        DEFAULT_PLACEMENT["light_direction"]
    )

    try:

        x = float(x)
        y = float(y)
        scale_ratio = float(scale_ratio)

    except (TypeError, ValueError):

        return DEFAULT_PLACEMENT

    x = min(max(x, 0.0), 0.9)

    y = min(max(y, 0.2), 0.85)

    scale_ratio = min(max(scale_ratio, 0.1), 0.5)

    valid_directions = [
        "left", "right", "top", "top-left", "top-right", "front"
    ]

    if light_direction not in valid_directions:

        light_direction = "front"

    return {
        "recommended_position": {"x": x, "y": y},
        "scale_ratio": scale_ratio,
        "light_direction": light_direction,
    }


LIGHT_SHADOW_OFFSETS = {
    "left": (0.06, 0.03),
    "right": (-0.06, 0.03),
    "top": (0.0, 0.05),
    "top-left": (0.05, 0.05),
    "top-right": (-0.05, 0.05),
    "front": (0.0, 0.04),
}


def estimate_room_brightness(room: Image.Image) -> float:

    grayscale = room.convert("L")

    histogram = grayscale.histogram()

    pixels = sum(histogram)

    brightness = sum(
        i * count for i, count in enumerate(histogram)
    ) / pixels

    return brightness


def harmonize_brightness(cutout: Image.Image, room_brightness: float) -> Image.Image:

    # Ürünün kendi rengini/malzemesini DEĞİŞTİRMEDEN, sadece hafif
    # bir parlaklık uyumu yapıyoruz — dar bir aralıkta (0.9-1.1)
    # tutuyoruz ki ürün görünüşü bozulmasın.

    baseline = 140.0

    factor = room_brightness / baseline

    factor = min(max(factor, 0.9), 1.1)

    enhancer = ImageEnhance.Brightness(cutout)

    return enhancer.enhance(factor)


def add_soft_shadow(cutout: Image.Image, light_direction: str):

    alpha = cutout.split()[3]

    shadow = Image.new("RGBA", cutout.size, (0, 0, 0, 0))

    shadow_alpha = alpha.point(lambda p: 80 if p > 10 else 0)

    shadow.putalpha(shadow_alpha)

    blur_radius = max(cutout.width, cutout.height) // 35 or 1

    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    dx_frac, dy_frac = LIGHT_SHADOW_OFFSETS.get(
        light_direction, (0.0, 0.04)
    )

    pad_x = int(cutout.width * 0.3)

    pad_y = int(cutout.height * 0.3)

    canvas = Image.new(
        "RGBA",
        (cutout.width + pad_x * 2, cutout.height + pad_y * 2),
        (0, 0, 0, 0)
    )

    shadow_offset_x = pad_x + int(cutout.width * dx_frac)

    shadow_offset_y = (
        pad_y
        + int(cutout.height * dy_frac)
        + int(cutout.height * 0.05)
    )

    canvas.alpha_composite(shadow, (shadow_offset_x, shadow_offset_y))

    canvas.alpha_composite(cutout, (pad_x, pad_y))

    return canvas, pad_x, pad_y


def composite_product_in_room(
    room_image_bytes: bytes,
    product_cutout: Image.Image,
    placement: dict
) -> bytes:

    room = Image.open(io.BytesIO(room_image_bytes)).convert("RGBA")

    room_w, room_h = room.size

    room_brightness = estimate_room_brightness(room.convert("RGB"))

    harmonized_cutout = harmonize_brightness(product_cutout, room_brightness)

    position = placement["recommended_position"]

    scale_ratio = placement["scale_ratio"]

    light_direction = placement["light_direction"]

    target_w = max(int(scale_ratio * room_w), 10)

    scale = target_w / harmonized_cutout.width

    target_h = int(harmonized_cutout.height * scale)

    resized = harmonized_cutout.resize(
        (target_w, target_h), Image.LANCZOS
    )

    with_shadow, pad_x, pad_y = add_soft_shadow(resized, light_direction)

    paste_x = int(position["x"] * room_w) - pad_x

    paste_y = int(position["y"] * room_h) - pad_y

    room.alpha_composite(with_shadow, (paste_x, paste_y))

    output = io.BytesIO()

    room.convert("RGB").save(output, format="JPEG", quality=92)

    return output.getvalue()


def render_product_in_room(
    room_image_bytes: bytes,
    room_content_type: str,
    product_image_url: str,
    product_name: str,
    client_id: str
):

    allowed, usage_count = check_and_increment_render_usage(client_id)

    if not allowed:

        return {
            "image_base64": None,
            "error": (
                "Günlük render limitine ulaştınız "
                f"({RENDER_DAILY_LIMIT}/gün). Lütfen yarın "
                "tekrar deneyin."
            )
        }

    try:

        product_image_bytes = download_image_bytes(product_image_url)

    except Exception as e:

        print("RENDER: ÜRÜN GÖRSELİ İNDİRME HATASI:", repr(e))

        return {"image_base64": None, "error": "Ürün görseli indirilemedi."}

    try:

        print("RENDER: arka plan kaldırılıyor...")

        cutout = cutout_product(product_image_bytes)

    except Exception as e:

        print("RENDER: ARKA PLAN KALDIRMA HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Ürün görseli işlenirken hata oluştu."
        }

    analysis = analyze_placement(
        room_image_bytes,
        room_content_type,
        product_name
    )

    placement = resolve_placement(analysis)

    print("RENDER: kullanılan yerleşim:", placement)

    try:

        result_bytes = composite_product_in_room(
            room_image_bytes,
            cutout,
            placement
        )

    except Exception as e:

        print("RENDER: KOMPOZİSYON HATASI:", repr(e))

        return {
            "image_base64": None,
            "error": "Görsel oluşturulurken hata oluştu."
        }

    image_b64 = base64.b64encode(result_bytes).decode("utf-8")

    return {
        "image_base64": image_b64,
        "error": None,
        "usage_count": usage_count,
        "usage_limit": RENDER_DAILY_LIMIT
    }