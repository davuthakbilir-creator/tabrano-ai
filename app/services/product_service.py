import json

from app.database.product_repository import (
    get_all_products,
    search_products
)



def get_products():

    products = get_all_products()

    return format_products(products)




def find_products(
    query,
    category=None,
    color=None,
    material=None,
    max_price=None
):

    products = search_products(
        query,
        category,
        color,
        material,
        max_price
    )


    return format_products(products)





def parse_variants(raw_variants):

    if not raw_variants:
        return []

    try:

        return json.loads(raw_variants)

    except (TypeError, ValueError):

        return []


def parse_style_profile(raw_profile):

    if not raw_profile:
        return {}

    try:

        return json.loads(raw_profile)

    except (TypeError, ValueError):

        return {}



def format_products(products):

    result = []


    for p in products:

        result.append({

            "id": p[0],

            "stock_code": p[1],

            "name": p[2],

            "category": p[3],

            "description": p[4],


            "width": p[5],

            "depth": p[6],

            "height": p[7],


            "price": p[8],


            "url": p[9],

            "image": p[10],


            "color": p[11] or "",

            "material": p[12] or "",

            "style": p[13] or "",


            "category_name": p[14] or "",

            "category_url": p[15] or "",


            "variants": parse_variants(p[16]),

            "style_profile": parse_style_profile(p[17])

            

        })


    return result

from app.database.product_repository import get_distinct_categories


def get_categories():

    return get_distinct_categories()

from app.database.product_repository import get_products_by_ids


def get_products_for_style_matching(ids):

    rows = get_products_by_ids(ids)

    return format_products(rows)