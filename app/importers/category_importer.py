from app.services.site_search_service import (
    get_product_urls,
    get_category_urls,
    extract_category,
    PRODUCT_URL_CACHE
)

from app.database.connection import get_connection



def clear_categories():

    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute(
        "DELETE FROM categories"
    )


    conn.commit()

    cursor.close()
    conn.close()




def insert_category(category):

    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute(
        """
        INSERT INTO categories
        (
            name,
            parent,
            url,
            product_count
        )

        VALUES
        (%s,%s,%s,%s)

        ON CONFLICT(url)
        DO UPDATE SET

        name = EXCLUDED.name,

        parent = EXCLUDED.parent,

        product_count = EXCLUDED.product_count

        """,

        (
            category["name"],
            category["parent"],
            category["url"],
            category["product_count"]
        )

    )


    conn.commit()

    cursor.close()

    conn.close()




def sync_categories():


    products = get_product_urls()


    PRODUCT_URL_CACHE.update(
        products
    )


    categories = get_category_urls()


    clear_categories()


    added = 0


    for url in categories:


        data = extract_category(
            url
        )


        if not data:

            continue



        insert_category(
            data
        )


        print(
            data
        )


        added += 1



    print(
        f"\n✅ {added} kategori PostgreSQL'e aktarıldı."
    )





if __name__ == "__main__":

    sync_categories()