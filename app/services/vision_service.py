from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import base64
from collections import defaultdict
from datetime import date

from app.services.product_service import find_products, get_categories


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=60.0
)


ALLOWED_CONTENT_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
]

MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024

DAILY_ANALYZE_LIMIT = 5

_usage_counter = defaultdict(lambda: defaultdict(int))


def check_and_increment_usage(client_id: str):

    today = date.today().isoformat()

    count = _usage_counter[client_id][today]

    if count >= DAILY_ANALYZE_LIMIT:

        return False, count


    _usage_counter[client_id][today] = count + 1

    return True, count + 1


BASE_ANALYSIS_PROMPT_TEMPLATE = """
Sen bir iç mimar / dekorasyon danışmanısın.

Sana bir oda fotoğrafı verilecek. Fotoğrafı analiz et ve
SADECE aşağıdaki alanları içeren bir JSON döndür:

- room_type: oda tipi (örn. "Oturma Odası", "Yatak Odası", "Yemek Odası")
- style: dekorasyon stili (örn. "Modern", "Minimalist", "Klasik", "İskandinav")
- colors: odada baskın olan 2-4 renk, liste olarak (örn. ["Beyaz", "Bej", "Ceviz"])
- existing_furniture: odada zaten var olan mobilyalar, kısa liste
- empty_areas: odada boş/eksik kalan alanlar, kısa liste (örn. ["köşe boş", "sehpa yok"])
- suggested_categories: bu odaya uygun olabilecek Tabrano ürün kategorileri, liste olarak.

  ÇOK ÖNEMLİ: suggested_categories alanına SADECE aşağıdaki listede
  BİREBİR (harfi harfine) geçen kategori isimlerini yaz. Bu listenin
  dışında bir kategori UYDURMA, kısaltma veya genelleştirme yapma
  (örneğin oda mutfaksa "Bahçe Masası" seçme, "Çalışma Masası" seçme
  — sadece odaya gerçekten uygun olan spesifik ismi seç).

  AYRICA ÇOK ÖNEMLİ: Kullanıcının mesajında belirli bir ürün türü
  geçiyorsa (örn. "masa öner", "sandalye öner", "TV ünitesi öner"),
  suggested_categories alanına SADECE o türle eşleşen kategorileri
  yaz. Kullanıcı sadece masa istemişse "sandalye" ekleme, kullanıcı
  sadece sandalye istemişse "masa" ekleme — kendi inisiyatifinle
  tamamlayıcı/ilişkili ürün önerme. Kullanıcı mesajında spesifik bir
  ürün türü geçmiyorsa (örn. sadece "mutfağım için öneri yap" gibi
  genel bir istekse), o zaman odaya uygun birden fazla kategori
  önerebilirsin.

  Gerçek kategori listesi:
  {category_list}

- recommendations: kullanıcıya gösterilecek, 2-4 maddelik kısa ve
  doğal dekorasyon önerisi cümleleri (liste olarak)

Sadece JSON döndür, başka hiçbir metin ekleme, kod bloğu (```) kullanma.
"""


def build_analysis_prompt(user_message):

    try:

        categories = get_categories()

    except Exception as e:

        print("VISION: KATEGORİ LİSTESİ ALINAMADI:", repr(e))

        categories = []


    category_list_text = (
        "\n".join(f"- {c}" for c in categories)
        if categories else "(kategori listesi alınamadı)"
    )


    prompt = BASE_ANALYSIS_PROMPT_TEMPLATE.format(
        category_list=category_list_text
    )

    if user_message and user_message.strip():

        prompt += f"""

Kullanıcının özel isteği: "{user_message.strip()}"

Bu isteği MUTLAKA dikkate al. suggested_categories, colors ve
recommendations alanlarını kullanıcının bu isteğine göre
önceliklendir. Örneğin kullanıcı belirli bir ürün tipi veya renk
istediyse (örn. "ceviz rengi masa"), bunu suggested_categories ve
colors alanlarına yansıt — ama suggested_categories için hâlâ
sadece yukarıdaki gerçek kategori listesinden seç.
"""

    return prompt


def strip_code_fence(text):

    text = text.strip()

    if text.startswith("```"):

        text = text.strip("`")

        if text.lower().startswith("json"):

            text = text[4:].strip()

    return text


def call_vision_model(image_bytes, content_type, user_message=""):

    print("VISION: base64 encode başlıyor, boyut:", len(image_bytes))

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    data_url = f"data:{content_type};base64,{b64_image}"


    prompt = build_analysis_prompt(user_message)


    print("VISION: OpenAI'a istek gönderiliyor...")


    try:

        response = client.responses.create(
            model="gpt-5.5",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url
                        }
                    ]
                }
            ]
        )

    except Exception as e:

        print("VISION: OpenAI ÇAĞRISI HATASI:", repr(e))

        raise


    print("VISION: OpenAI'dan cevap geldi")


    text = strip_code_fence(
        response.output_text
    )


    try:

        return json.loads(text)

    except json.JSONDecodeError as e:

        print(
            "VISION JSON PARSE HATASI:",
            e,
            "RAW:",
            text
        )

        return {}


def find_matching_products(categories, colors):

    products = []
    seen = set()


    color = colors[0] if colors else None


    search_categories = categories if categories else [""]


    for category in search_categories[:3]:

        results = find_products(
            category,
            category=category,
            color=color
        )


        if not results and color:

            print(
                f"VISION: '{category}' + '{color}' ile sonuç yok, "
                "renk filtresi kaldırılıp tekrar deneniyor..."
            )

            results = find_products(
                category,
                category=category,
                color=None
            )


        for product in results:

            if product["id"] in seen:
                continue

            seen.add(product["id"])
            products.append(product)


    return products[:6]


def analyze_room(image_bytes, content_type, client_id, user_message=""):

    print("VISION: analyze_room çağrıldı, client_id:", client_id, "mesaj:", user_message)


    allowed, usage_count = check_and_increment_usage(
        client_id
    )

    if not allowed:

        return {
            "room_style": "",
            "colors": "",
            "recommendations": [],
            "products": [],
            "error": (
                "Günlük fotoğraf analizi limitine ulaştınız "
                f"({DAILY_ANALYZE_LIMIT}/gün). Lütfen yarın "
                "tekrar deneyin."
            )
        }


    analysis = call_vision_model(
        image_bytes,
        content_type,
        user_message
    )

    print("VISION: ham analiz sonucu:", analysis)


    room_type = analysis.get("room_type", "")

    style = analysis.get("style", "")

    colors = analysis.get("colors", [])

    if not isinstance(colors, list):

        colors = [colors] if colors else []


    suggested_categories = analysis.get(
        "suggested_categories",
        []
    )

    if not isinstance(suggested_categories, list):

        suggested_categories = (
            [suggested_categories]
            if suggested_categories else []
        )


    recommendations = analysis.get(
        "recommendations",
        []
    )

    if not isinstance(recommendations, list):

        recommendations = (
            [recommendations]
            if recommendations else []
        )


    products = find_matching_products(
        suggested_categories,
        colors
    )


    room_style = ", ".join(
        filter(None, [room_type, style])
    )


    return {
        "room_style": room_style,
        "colors": ", ".join(colors),
        "recommendations": recommendations,
        "products": [
            {
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "url": p["url"],
                "image": p.get("image")
            }
            for p in products
        ],
        "usage_count": usage_count,
        "usage_limit": DAILY_ANALYZE_LIMIT
    }