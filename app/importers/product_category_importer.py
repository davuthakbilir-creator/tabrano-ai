from app.services.site_search_service import get_product_urls
from app.services.site_search_service import extract_product

from app.database.product_repository import (
    update_product_category
)



def sync_categories():

    products = get_product_urls()

    print("Ürün sayısı:", len(products))


    count = 0


    for url in products:

        print("Kontrol:", url)


        data = extract_product(url)


        if not data:
            continue


        category = data.get(
    "category"
)

        if category:

            update_product_category(
                url,
                category
            )

            count += 1



    print(
        "Kategori güncellenen ürün:",
        count
    )



if __name__ == "__main__":

    sync_categories()