import pandas as pd
import re
from pathlib import Path

from app.database.product_repository import (
    clear_products,
    insert_product
)


BASE_DIR = Path(__file__).resolve().parent.parent


PRODUCT_FILE = BASE_DIR / "imports" / "products.xlsx"
IMAGE_FILE = BASE_DIR / "imports" / "product_images.xlsx"



def slugify(text):

    text = str(text).lower()


    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c"
    }


    for old, new in replacements.items():
        text = text.replace(old, new)


    text = re.sub(
        r"[^a-z0-9]+",
        "-",
        text
    )


    return text.strip("-")

def extract_color(description):

    text = str(description).lower()

    colors = [
    "siyah",
    "beyaz",
    "ceviz",
    "gold",
    "gümüş",
    "antrasit",
    "bej",
    "kahve",
    "kahverengi",
    "meşe",
    "füme",
    "krem",
    "vizon",
    "bronz",
    "krom",
    "titanyum",
    "gri",
    "yeşil",
    "mavi",
    "lacivert",
    "bordo",
    "somon",
    "vizon"
]

    found = []

    for color in colors:
        if color in text:
            found.append(color)

    return ", ".join(found)



def extract_material(description):

    text = str(description).lower()

    materials = [
        "metal",
        "mdf",
        "ahşap",
        "mermer",
        "cam",
        "suntalam",
        "masif"
    ]

    found = []

    for material in materials:
        if material in text:
            found.append(material)

    return ", ".join(found)

def load_data():

    products = pd.read_excel(PRODUCT_FILE)
    images = pd.read_excel(IMAGE_FILE)


    print("ÜRÜN KOLONLARI:")
    print(products.columns.tolist())


    print("\nGÖRSEL KOLONLARI:")
    print(images.columns.tolist())


    print("\nGÖRSEL TEST:")
    print(
        images[
            [
                "Urun Kartı ID",
                "Resim Adı"
            ]
        ].head(5)
    )


    return products, images




def build_image_map(images):

    image_map = {}


    base_url = (
        "https://static.ticimax.cloud/"
        "cdn-cgi/image/width=-,quality=85,format=webp/"
        "75297/uploads/urunresimleri/buyuk/"
    )


    for _, row in images.iterrows():

        product_id = int(
            row["Urun Kartı ID"]
        )


        image_name = row["Resim Adı"]


        if (
            product_id not in image_map
            and isinstance(image_name, str)
            and image_name.strip()
        ):

            image_map[product_id] = (
                base_url + image_name
            )



    print(
        "GÖRSEL MAP:",
        len(image_map)
    )


    print(
        "İLK GÖRSELLER:",
        list(image_map.items())[:5]
    )


    return image_map




def get_product_price(row):

    discount_price = row.get(
        "INDIRIMLIFIYAT"
    )


    normal_price = row.get(
        "SATISFIYATI"
    )


    if pd.notna(discount_price):

        try:
            if float(discount_price) > 0:
                return discount_price
        except:
            pass


    return normal_price




def sync_products():


    products, images = load_data()


    image_map = build_image_map(images)


    clear_products()


    added = 0
    processed_cards = set()



    for _, row in products.iterrows():


        product_id = int(
            row["URUNKARTIID"]
        )


        if product_id in processed_cards:
            continue


        processed_cards.add(product_id)



        product_name = str(
            row.get(
                "URUNADI",
                ""
            )
        )



        product = {


            "product_card_id": product_id,


            "stock_code": str(
                row.get(
                    "STOKKODU",
                    ""
                )
            ),


            "name": product_name,


            "category": str(
                row.get(
                    "KATEGORILER",
                    ""
                )
            ),


            "description": str(
                row.get(
                    "ACIKLAMA",
                    ""
                )
            ),
            "color": extract_color(
    row.get(
        "ACIKLAMA",
        ""
    )
),


"material": extract_material(
    row.get(
        "ACIKLAMA",
        ""
    )
),


"style": "",


            "width": row.get(
                "URUNGENISLIK"
            ),


            "depth": row.get(
                "URUNDERINLIK"
            ),


            "height": row.get(
                "URUNYUKSEKLIK"
            ),


            "price": get_product_price(row),


            "url": (
                "https://tabrano.com/"
                + slugify(product_name)
            ),


            "image": image_map.get(
                product_id,
                ""
            ),


            "is_active": True

        }



        print(
            product["product_card_id"],
            product["name"],
            product["url"]
        )



        insert_product(product)


        added += 1



    print(
        f"\n✅ {added} ürün PostgreSQL'e aktarıldı."
    )




if __name__ == "__main__":

    sync_products() 