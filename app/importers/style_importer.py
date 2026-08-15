import json
import time

from app.database.connection import get_connection
from app.services.style_analysis_service import analyze_product_style


def get_products_needing_style_analysis():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_card_id, name, description, color, material, image
        FROM products
        WHERE (style_profile IS NULL OR style_profile = '{}')
          AND image IS NOT NULL AND image != ''
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def save_style_profile(product_card_id, profile):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE products SET style_profile = %s WHERE product_card_id = %s",
        (json.dumps(profile, ensure_ascii=False), product_card_id)
    )

    conn.commit()

    cursor.close()
    conn.close()


def run():

    products = get_products_needing_style_analysis()

    print(f"Stil analizi bekleyen ürün sayısı: {len(products)}")

    count = 0

    for product_card_id, name, description, color, material, image in products:

        print(f"Analiz ediliyor: {name}")

        profile = analyze_product_style(
            name, description, color, material, image
        )

        if profile:

            save_style_profile(product_card_id, profile)

            count += 1

        else:

            print(f"  -> analiz başarısız, atlandı: {name}")

        # Rate limit'e takılmamak için kısa bekleme
        time.sleep(0.5)

    print(f"Tamamlandı: {count}/{len(products)} ürün için stil profili çıkarıldı.")


if __name__ == "__main__":

    run()