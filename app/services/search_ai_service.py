from openai import OpenAI
from dotenv import load_dotenv
import os
import json


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def build_history_context(history):

    if not history:
        return ""


    lines = []


    for item in history[-6:]:

        role = item.get("role", "")
        content = item.get("content", "")

        if not content:
            continue

        lines.append(
            f"{role}: {content}"
        )


    if not lines:
        return ""


    return (
        "\n\nSohbet geçmişi (bağlam için):\n"
        + "\n".join(lines)
    )


def get_category_list_text():

    try:

        from app.services.product_service import get_categories

        categories = get_categories()

    except Exception as e:

        print("SEARCH_AI: KATEGORİ LİSTESİ ALINAMADI:", repr(e))

        categories = []


    if not categories:

        return "(kategori listesi alınamadı)"


    return "\n".join(f"- {c}" for c in categories)


def analyze_search(message: str, history: list = None):

    history_context = build_history_context(
        history
    )

    category_list_text = get_category_list_text()


    response = client.responses.create(
        model="gpt-5.5",
        input=f"""
Sen bir mobilya arama analizcisisin.

Kullanıcının mesajını JSON formatına çevir.

Alanlar:

- query: aranacak ürün
- category: ürün kategorisi
- max_price: maksimum fiyat
- min_price: minimum fiyat
- color: renk
- material: malzeme
- size: ölçü
- style: kullanıcının bahsettiği iç mimari stili (örn. "Japandi",
"Modern", "Minimalist", "Lüks", "İskandinav", "Klasik", "Rustik",
"Endüstriyel", "Bohem") — kullanıcı mesajında bir stil/tarz
kelimesi geçiyorsa (örn. "İskandinav tarzı", "modern görünüm",
"Japandi oda") bunu style alanına MUTLAKA yaz, boş bırakma. Sadece
gerçekten hiçbir stil ipucu yoksa boş bırak.

ÇOK ÖNEMLİ - category alanı için kural:

category alanına SADECE aşağıdaki listede BİREBİR (harfi harfine)
geçen bir kategori adı yaz. Bu listenin dışında bir kategori
UYDURMA, kısaltma veya genelleştirme yapma.

Kullanıcının kullandığı kelime listedeki hiçbir kategoriyle tam
örtüşmüyorsa (örn. "bahçe takımı" dediğinde listede sadece "Bahçe
Sandalyesi", "Bahçe Koltukları", "Bahçe Oturma Grupları", "Bahçe
Masası" varsa), en yakın/mantıklı olan kategoriyi seç — ama yine
MUTLAKA listeden birebir bir isim kullan. Hiçbiri mantıklı
gelmiyorsa category alanını boş bırak, query alanını yine
kullanıcının kullandığı kelimeyle doldur (serbest metin arama
devam etsin).

Gerçek kategori listesi:
{category_list_text}


Önemli kural:

Kullanıcının mesajında ürün tipi/kategorisi belirtilmemişse
(örneğin sadece renk, malzeme veya fiyat gibi bir filtre
belirtmişse), sohbet geçmişine bak ve en son bahsedilen ürün
tipini/kategorisini query ve category alanlarına taşı.

Örnek: Önceki mesajda "zigon sehpa" aranmış, kullanıcı şimdi
sadece "beyaz olsun" diyorsa:
query: "zigon sehpa", category: "sehpa", color: "beyaz"

{history_context}


Kullanıcının şimdiki mesajı:

{message}


Sadece JSON döndür, başka hiçbir metin ekleme.
"""
    )


    text = response.output_text.strip()


    if text.startswith("```"):

        text = text.strip("`")

        if text.lower().startswith("json"):

            text = text[4:].strip()


    try:

        return json.loads(text)

    except json.JSONDecodeError as e:

        print(
            "SEARCH JSON PARSE HATASI:",
            e,
            "RAW:",
            text
        )

        return {}