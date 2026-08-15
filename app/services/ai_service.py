from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os

from app.services.product_service import find_products, get_products
from app.services.search_ai_service import analyze_search


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


PROMPT_PATH = Path("app/prompts/system_prompt.txt")


STYLE_CANDIDATE_LIMIT = 40



def load_system_prompt():

    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()



def filter_by_color(products, color):

    if not color:
        return products


    color_lower = color.lower()


    return [
        p for p in products
        if color_lower in (p.get("color") or "").lower()
    ]




def ask_ai(
    message: str,
    history: list
):

    system_prompt = load_system_prompt()


    trimmed_history = history[-10:] if history else []


    search_data = analyze_search(
        message,
        trimmed_history
    )


    query = search_data.get("query")

    category = search_data.get("category")

    color = search_data.get("color")

    material = search_data.get("material")

    max_price = search_data.get("max_price")

    min_price = search_data.get("min_price")

    style = search_data.get("style")



    print("SEARCH DATA:", search_data)


    # Ne query ne style varsa gerçekten normal sohbet

    if not query and not style:

        input_messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        input_messages.extend(
            trimmed_history
        )

        input_messages.append(
            {
                "role": "user",
                "content": message
            }
        )


        response = client.responses.create(
            model="gpt-5.5",
            input=input_messages
        )


        return {
            "answer": response.output_text,
            "products": []
        }




    products = []

    seen = set()



    if query:

        results = find_products(
            query,
            category=category,
            color=color,
            material=material,
            max_price=max_price
        )


        if not results and color:

            print(
                f"AI_SERVICE: '{query}' + '{color}' ile sonuç yok, "
                "renk filtresi kaldırılıp tekrar deneniyor..."
            )

            results = find_products(
                query,
                category=category,
                color=None,
                material=material,
                max_price=max_price
            )


        if category and len(results) < 5:

            category_root = category.split()[0] if category.split() else category

            print(
                f"AI_SERVICE: '{category}' kategorisinde az sonuç "
                f"({len(results)}), '{category_root}' kök kelimesiyle "
                "genişletiliyor..."
            )

            broader_results = find_products(
                category_root,
                category=category_root,
                color=color,
                material=material,
                max_price=max_price
            )

            existing_ids = {p["id"] for p in results}

            for product in broader_results:

                if product["id"] not in existing_ids:

                    results.append(product)
                    existing_ids.add(product["id"])


            if len(results) < 3:

                print(
                    f"AI_SERVICE: kök kelimeyle de az sonuç "
                    f"({len(results)}), kategori tamamen kaldırılıyor..."
                )

                fallback_results = find_products(
                    category_root,
                    category=None,
                    color=color,
                    material=material,
                    max_price=max_price
                )

                for product in fallback_results:

                    if product["id"] not in existing_ids:

                        results.append(product)
                        existing_ids.add(product["id"])


        for product in results:

            if product["id"] in seen:
                continue

            seen.add(product["id"])

            products.append(product)


        if color and any(
            color.lower() in (p.get("color") or "").lower()
            for p in products
        ):

            products = filter_by_color(
                products,
                color
            )



    # -----------------------------------------------------
    # STİL BAZLI GENİŞLETİLMİŞ ARAMA
    # -----------------------------------------------------
    # Kullanıcı bir stil belirtti ("İskandinav tarzı" gibi) ama
    # normal anahtar kelime araması az/hiç sonuç getirmediyse
    # (örn. "mobilyalar" gibi genel bir kelime kullanıldıysa),
    # kategoriye (varsa) ya da tüm katalogdaki stil profili
    # çıkarılmış ürünlere bakıp GPT ile stil uyumuna göre
    # sıralıyoruz — literal kelime eşleşmesine bağımlı kalmadan.

    if style and len(products) < 3:

        print(f"AI_SERVICE: stil bazlı genişletilmiş arama tetiklendi: '{style}'")

        if category:

            broad_results = find_products(
                "",
                category=category,
                color=color,
                material=material,
                max_price=max_price
            )

        else:

            broad_results = get_products()


        candidates = [
            p for p in broad_results
            if p.get("style_profile")
        ][:STYLE_CANDIDATE_LIMIT]


        if candidates:

            from app.services.style_match_service import rank_products_by_style

            ranked = rank_products_by_style(style, candidates)

            existing_ids = {p["id"] for p in products}

            for p in ranked:

                if p["id"] not in existing_ids:

                    products.append(p)
                    existing_ids.add(p["id"])

        else:

            print("AI_SERVICE: stil profili çıkarılmış aday ürün bulunamadı")



    elif style and products:

        from app.services.style_match_service import rank_products_by_style
        from app.services.product_service import get_products_for_style_matching

        product_ids = [p["id"] for p in products]

        full_products = get_products_for_style_matching(product_ids)

        products = rank_products_by_style(style, full_products)



    products = products[:5]




    if products:


        product_text = ""


        for product in products:


            product_text += f"""

Ürün Adı: {product["name"]}

Kategori: {product["category"]}

Renk: {product.get("color","")}

Malzeme: {product.get("material","")}

Fiyat: {product["price"]} TL

"""



        user_prompt = f"""

Kullanıcının mesajı:

{message}


Tabrano veritabanındaki uygun ürünler:

{product_text}


Kurallar:

- Sadece yukarıda verilen ürünleri ve bilgilerini kullan; ürün adı, renk, malzeme veya fiyat uydurma.
- Her ürünün adında geçen mobilya tipini birebir koru (sehpa, dresuar, konsol, masa, sandalye vb.) — asla farklı bir mobilya tipiyle karıştırma veya yanlış tipte tanıtma.
- En fazla 5 ürün öner, kısa bir giriş cümlesiyle başla.
- URL yazma, uzun katalog metni yazma — doğal bir mobilya danışmanı gibi kısa ve net konuş.
- Kullanıcı önceki mesajlara atıfta bulunuyorsa ("ikincisi", "az önce bahsettiğin", "ilk gösterdiğin" gibi), sohbet geçmişindeki bağlamı kullanarak doğru ürüne referans ver.
- Eğer gösterilen ürünler kullanıcının istediği tam renk/ölçüyle
  birebir eşleşmiyorsa (örn. tam o renk yoksa), bunu doğal bir
  şekilde belirt ("tam o renkte bulamadım ama şunlar yakın
  durabilir" gibi) — ama SORU SORMA, doğrudan elindeki ürünleri sun.

"""



    else:


        user_prompt = f"""

Kullanıcının mesajı:

{message}


Uygun ürün bulunamadı.


Kurallar:

- Kullanıcıya "renk/ölçü/tarz belirtir misiniz" gibi soru SORMA.
- Bunun yerine, aradığı şeye en yakın olabilecek genel bir kategori
  önerisi yap ve kısaca "şu an elimizde tam eşleşen ürün yok ama
  şunlara bakabilirsiniz" tarzında yönlendir.
- Ürün uydurma, var olmayan bir ürünü varmış gibi gösterme.
- Kısa ve doğal konuş, uzun açıklama yapma.
- Kullanıcı önceki mesajlarda bir ürün/kategoriden bahsettiyse, o bağlamı unutma; yeniden başa dönüp "ne arıyordunuz" diye sorma.

"""




    input_messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    input_messages.extend(
        trimmed_history
    )

    input_messages.append(
        {
            "role": "user",
            "content": user_prompt
        }
    )


    response = client.responses.create(
        model="gpt-5.5",
        input=input_messages
    )




    return {

        "answer": response.output_text,


        "products": [

            {
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "url": p["url"],
                "image": p.get("image")
            }

            for p in products

        ]

    }