import json

from app.services.site_search_service import (
    get_product_urls,
    extract_product
)

from app.database.product_repository import (
    clear_products,
    insert_product
)



def sync_from_site():

    urls = get_product_urls()


    print(
        "Bulunan ürün:",
        len(urls)
    )


    clear_products()


    count = 0


    for url in urls:


        print(
            "Çekiliyor:",
            url
        )


        product = extract_product(
            url
        )


        if not product:
            continue



        data = {

            "product_card_id": count,

            "stock_code": "",

            "name": product["name"],

            "category": "",

            "description": product["description"],

            "width": product.get("width"),

            "depth": product.get("depth"),

            "height": product.get("height"),

            "price": product.get("price"),

            "url": product["url"],

            "image": product["image"],

            "color": product.get("color", ""),

            "material": product.get("material", ""),

            "style": product.get("product_type", ""),

            "is_active": True,

            "variants": json.dumps(
                product.get("variants", []),
                ensure_ascii=False
            )

        }


        insert_product(
            data
        )


        count += 1



    print(
        "Tamamlandı:",
        count
    )



if __name__ == "__main__":

    sync_from_site()