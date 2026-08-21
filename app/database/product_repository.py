from app.database.connection import get_connection



def clear_products():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM products
    """)

    conn.commit()

    cursor.close()
    conn.close()

    print("🗑️ Products tablosu temizlendi.")





def insert_product(product):

    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO products (
            product_card_id,
            stock_code,
            name,
            category,
            description,
            width,
            depth,
            height,
            price,
            url,
            image,
            color,
            material,
            style,
            is_active,
            variants
        )

        VALUES (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s
        )

    """, (

        product.get("product_card_id"),
        product.get("stock_code"),
        product.get("name"),
        product.get("category"),
        product.get("description"),

        product.get("width"),
        product.get("depth"),
        product.get("height"),

        product.get("price"),

        product.get("url"),
        product.get("image"),

        product.get("color", ""),
        product.get("material", ""),
        product.get("style", ""),

        product.get("is_active", True),

        product.get("variants", "[]")

    ))


    conn.commit()

    cursor.close()
    conn.close()






def get_all_products():

    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            product_card_id,
            stock_code,
            name,
            category,
            description,
            width,
            depth,
            height,
            price,
            url,
            image,
            color,
            material,
            style,
            category_name,
            category_url,
            variants,
            style_profile

        FROM products

        ORDER BY name
    """)


    rows = cursor.fetchall()


    cursor.close()
    conn.close()


    return rows






def search_products(
    keyword,
    category=None,
    color=None,
    material=None,
    max_price=None
):

    conn = get_connection()
    cursor = conn.cursor()


    query = """
        SELECT
            product_card_id,
            stock_code,
            name,
            category,
            description,
            width,
            depth,
            height,
            price,
            url,
            image,
            color,
            material,
            style,
            category_name,
            category_url,
            variants,
            style_profile

        FROM products

        WHERE
        (
            LOWER(name) LIKE LOWER(%s)
            OR LOWER(category) LIKE LOWER(%s)
            OR LOWER(description) LIKE LOWER(%s)
            OR LOWER(category_name) LIKE LOWER(%s)
        )
    """


    params = [
        f"%{keyword}%",
        f"%{keyword}%",
        f"%{keyword}%",
        f"%{keyword}%"
    ]


    if category:

        query += """
        AND
        (
            LOWER(category) LIKE LOWER(%s)
            OR LOWER(category_name) LIKE LOWER(%s)
        )
        """

        params.extend([
            f"%{category}%",
            f"%{category}%"
        ])



    if color:

        query += """
        AND
        (
            LOWER(color) LIKE LOWER(%s)
            OR LOWER(name) LIKE LOWER(%s)
            OR LOWER(description) LIKE LOWER(%s)
        )
        """

        params.extend([
            f"%{color}%",
            f"%{color}%",
            f"%{color}%"
        ])



    if material:

        query += """
        AND LOWER(material) LIKE LOWER(%s)
        """

        params.append(
            f"%{material}%"
        )



    if max_price:

        query += """
        AND price <= %s
        """

        params.append(
            max_price
        )



    query += """
        ORDER BY name
        LIMIT 20
    """



    print("QUERY:")
    print(query)

    print("PARAMS:")
    print(params)



    cursor.execute(
        query,
        params
    )


    rows = cursor.fetchall()


    cursor.close()
    conn.close()


    return rows





def update_product_category(
    url,
    category
):

    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute(
        """
        UPDATE products

        SET
            category_name=%s,
            category_url=%s

        WHERE url=%s
        """,

        (
            category["name"],
            category["url"],
            url
        )
    )


    conn.commit()

    cursor.close()
    conn.close()


def get_products_by_ids(ids):

    if not ids:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            product_card_id, stock_code, name, category, description,
            width, depth, height, price, url, image,
            color, material, style, category_name, category_url,
            variants, style_profile
        FROM products
        WHERE product_card_id = ANY(%s)
        """,
        (ids,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def get_products_by_slugs(slugs):
    """`slugs` sondaki path parçasıdır (ör. 'rex-orta-sehpa'), tam URL değil.
    Ticimax'ın ürün kartı ID'si tabrano-ai'daki product_card_id ile birebir
    eşleşmediği için (product_card_id yalnızca bu DB'nin kendi sıra numarasıdır),
    ürünler arası eşleştirme URL slug'ı üzerinden yapılır."""

    if not slugs:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        r"""
        SELECT
            product_card_id, stock_code, name, category, description,
            width, depth, height, price, url, image,
            color, material, style, category_name, category_url,
            variants, style_profile
        FROM products
        WHERE regexp_replace(url, '^https?://(www\.)?[^/]+/?', '') = ANY(%s)
        """,
        (slugs,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows

def get_distinct_categories():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT category_name
        FROM products
        WHERE category_name IS NOT NULL AND category_name != ''
        ORDER BY category_name
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [row[0] for row in rows]