import requests
from bs4 import BeautifulSoup
import re
import json
import xml.etree.ElementTree as ET


PRODUCT_URL_CACHE = set()


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


BASE_URL = "https://tabrano.com"


PRODUCT_SITEMAP = (
    "https://tabrano.com/sitemap/products/0.xml"
)


CATEGORY_SITEMAP = (
    "https://tabrano.com/sitemap/categories/0.xml"
)


NAMESPACE = {
    "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
}


# -----------------------------------------------------
# TEKNİK ÖZELLİK PARSER (description metninden)
# -----------------------------------------------------

BOILERPLATE_MARKERS = [
    "kargo ve teslimat süreci",
    "iptal ve iade",
    "bakım ve temizlik",
    "garanti",
    "kullanım alanı",
    "etiketler",
    "havale ile ödeme",
]


def strip_boilerplate(description):

    cut_index = len(description)

    for marker in BOILERPLATE_MARKERS:

        match = re.search(
            re.escape(marker),
            description,
            re.IGNORECASE
        )

        if match and match.start() < cut_index:

            cut_index = match.start()

    return description[:cut_index].strip()


SPEC_LABELS = [
    "Ürün Tipi",
    "Malzeme",
    "Form",
    "Renk Seçenekleri",
    "Ölçü",
]

_LABEL_PATTERN = "|".join(re.escape(label) for label in SPEC_LABELS)

_SPEC_REGEX = re.compile(
    rf"({_LABEL_PATTERN})\s*:\s*(.*?)(?=(?:{_LABEL_PATTERN})\s*:|$)",
    re.IGNORECASE
)


def parse_dimensions(value):

    dims = {
        "width": None,
        "depth": None,
        "height": None
    }

    numbers = re.findall(
        r"\d+(?:[.,]\d+)?",
        value
    )

    numbers = [
        float(n.replace(",", "."))
        for n in numbers
    ]

    if len(numbers) >= 3:

        dims["width"] = numbers[0]
        dims["depth"] = numbers[1]
        dims["height"] = numbers[2]

    elif len(numbers) == 2:

        dims["width"] = numbers[0]
        dims["height"] = numbers[1]

    elif len(numbers) == 1:

        dims["height"] = numbers[0]

    return dims


def parse_product_specs(description):

    specs = {
        "product_type": "",
        "material": "",
        "color": "",
        "width": None,
        "depth": None,
        "height": None
    }

    if not description:
        return specs

    description = strip_boilerplate(description)

    for match in _SPEC_REGEX.finditer(description):

        label = match.group(1).strip().lower()
        value = match.group(2).strip(" .,;")

        if not value:
            continue

        if label == "malzeme":

            specs["material"] = value

        elif label == "renk seçenekleri":

            value = re.sub(r"\s*/\s*", ",", value)
            value = re.sub(r"\s*,\s*", ",", value)
            specs["color"] = value

        elif label == "ürün tipi":

            specs["product_type"] = value

        elif label == "ölçü":

            dims = parse_dimensions(value)
            specs["width"] = dims["width"]
            specs["depth"] = dims["depth"]
            specs["height"] = dims["height"]

    return specs


# -----------------------------------------------------
# SAYFA İÇİ JS MODELİNDEN (productDetailModel) VERİ ÇEKME
# -----------------------------------------------------

def extract_json_object(text, start_marker):

    idx = text.find(start_marker)

    if idx == -1:
        return None


    brace_start = text.find("{", idx)

    if brace_start == -1:
        return None


    depth = 0
    in_string = False
    escape = False


    for i in range(brace_start, len(text)):

        ch = text[i]

        if in_string:

            if escape:

                escape = False

            elif ch == "\\":

                escape = True

            elif ch == '"':

                in_string = False

        else:

            if ch == '"':

                in_string = True

            elif ch == "{":

                depth += 1

            elif ch == "}":

                depth -= 1

                if depth == 0:

                    return text[brace_start:i + 1]


    return None


def extract_product_detail_model(soup):

    scripts = soup.find_all("script")

    for script in scripts:

        text = script.string or script.get_text() or ""

        if "productDetailModel" in text:

            raw_json = extract_json_object(
                text,
                "productDetailModel"
            )

            if not raw_json:
                return None

            try:

                return json.loads(raw_json)

            except Exception as e:

                print(
                    "productDetailModel JSON PARSE HATASI:",
                    e
                )

                return None

    return None


def parse_variant_colors(detail_model):

    colors = []

    if not detail_model:
        return colors


    variant_data = detail_model.get(
        "productVariantData"
    ) or []


    for item in variant_data:

        group_label = (
            item.get("ekSecenekTipiTanim")
            or ""
        ).lower()

        if (
            "renk" not in group_label
            and
            "reng" not in group_label
        ):
            continue


        value = (
            item.get("tanim")
            or ""
        ).strip()

        if value:

            colors.append(value)


    return colors


def parse_product_price(detail_model):

    if not detail_model:
        return None


    price = detail_model.get(
        "productPriceKDVIncluded"
    )

    if price is None:

        price = detail_model.get(
            "productPrice"
        )

    if price is None:
        return None


    try:

        return float(price)

    except (TypeError, ValueError):

        return None


def extract_variants(detail_model):

    if not detail_model:

        print("VARIANTS DEBUG: detail_model YOK (None)")

        return []


    variant_data = detail_model.get(
        "productVariantData"
    ) or []

    products_list = detail_model.get(
        "products"
    ) or []


    print(
        "VARIANTS DEBUG: variant_data adedi:",
        len(variant_data),
        "products_list adedi:",
        len(products_list)
    )


    attributes_by_sku = {}

    for item in variant_data:

        sku_id = item.get("urunID")

        if sku_id is None:
            continue

        group = item.get("ekSecenekTipiTanim") or ""

        value = item.get("tanim") or ""

        if not group or not value:
            continue

        attributes_by_sku.setdefault(
            sku_id, {}
        )[group] = value


    variants = []


    for product in products_list:

        sku_id = product.get("id")

        if sku_id is None:
            continue


        image = (
            product.get("spotResimBuyukYolu")
            or product.get("spotResimYolu")
            or ""
        )


        price = (
            product.get("urunFiyatiOrjinal")
            or product.get("indirimliFiyati")
            or product.get("satisFiyati")
        )


        variants.append({

            "sku_id": sku_id,

            "stock_code": product.get("stokKodu", ""),

            "attributes": attributes_by_sku.get(sku_id, {}),

            "image": image,

            "price": price,

            "is_default": bool(product.get("anaUrun")),

            "is_active": bool(product.get("aktif", True)),

        })


    print(
        "VARIANTS DEBUG: sonuç olarak",
        len(variants),
        "varyant üretildi"
    )


    return variants


def merge_colors(*color_lists):

    seen = set()
    result = []

    for color_list in color_lists:

        for color in color_list:

            color = color.strip()

            if not color:
                continue

            key = color.lower()

            if key not in seen:

                seen.add(key)
                result.append(color)

    return result




def fetch_page(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        return BeautifulSoup(
            response.text,
            "lxml"
        )


    except Exception as e:

        print(
            "SAYFA HATASI:",
            url,
            e
        )

        return None





def get_sitemap_urls(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()


    root = ET.fromstring(
        response.text
    )


    urls = []


    for item in root.findall(
        "ns:url",
        NAMESPACE
    ):

        loc = item.find(
            "ns:loc",
            NAMESPACE
        )


        if loc is not None:

            urls.append(
                loc.text
            )


    return urls





def get_product_urls():

    urls = get_sitemap_urls(
        PRODUCT_SITEMAP
    )

    PRODUCT_URL_CACHE.update(
        urls
    )

    return urls





def get_category_urls():

    return get_sitemap_urls(
        CATEGORY_SITEMAP
    )






def extract_product_category(soup):


    breadcrumb = soup.find(
        class_=re.compile(
            "breadcrumb",
            re.I
        )
    )


    if not breadcrumb:
        return None



    links = breadcrumb.find_all(
        "a",
        href=True
    )



    if not links:
        return None



    categories = []



    for link in links:


        href = link.get(
            "href",
            ""
        )


        text = link.get_text(
            strip=True
        )


        if not text:
            continue


        if any(x in href.lower() for x in [
            "urun",
            "product"
        ]):
            continue



        if href.startswith("/"):

            href = (
                BASE_URL
                +
                href
            )


        categories.append({

            "name": text,

            "url": href

        })



    if not categories:

        return None



    if len(categories) >= 2:

       return categories[-2]


    return categories[-1]







def extract_product(url):

    soup = fetch_page(url)

    if not soup:
        return None


    name = ""

    h1 = soup.find("h1")

    if h1:
        name = h1.get_text(
            strip=True
        )


    description = ""

    desc = soup.find(
        "div",
        class_=re.compile(
            "description|aciklama|detail",
            re.I
        )
    )

    if desc:
        description = desc.get_text(
            " ",
            strip=True
        )


    # -----------------
    # TEKNİK ÖZELLİKLERİ PARSE ET (description'dan)
    # -----------------

    specs = parse_product_specs(
        description
    )


    # -----------------
    # SAYFA İÇİ JS MODELİNİ BİR KEZ PARSE ET
    # -----------------

    detail_model = extract_product_detail_model(
        soup
    )

    variants = extract_variants(detail_model)

    variant_colors = parse_variant_colors(
        detail_model
    )

    price = parse_product_price(
        detail_model
    )

    description_colors = (
        specs["color"].split(",")
        if specs["color"] else []
    )

    color = ",".join(
        merge_colors(
            description_colors,
            variant_colors
        )
    )


    # -----------------
    # GÖRSEL BULMA
    # -----------------

    image = ""


    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:
        image = og_image.get(
            "content",
            ""
        )


    if not image:

        imgs = soup.find_all(
            "img"
        )

        for img in imgs:

            src = (
                img.get("data-src")
                or img.get("src")
                or ""
            )


            if (
                "mic.gif" not in src
                and
                "logo" not in src.lower()
                and
                src
            ):

                image = src
                break



    if image.startswith("/"):

        image = (
            BASE_URL
            +
            image
        )



    category = extract_product_category(
        soup
    )


    return {

        "name": name,

        "description": description,

        "url": url,

        "image": image,

        "category": category,

        "color": color,

        "material": specs["material"],

        "product_type": specs["product_type"],

        "width": specs["width"],

        "depth": specs["depth"],

        "height": specs["height"],

        "price": price,

        "variants": variants

    }







def is_active_category(soup):


    text = soup.get_text(
        " ",
        strip=True
    ).lower()



    bad_words = [

        "ürün bulunamadı",

        "sonuç bulunamadı",

        "stokta ürün yok"

    ]



    for word in bad_words:

        if word in text:

            return False



    return True






def get_category_product_urls(url):


    products = set()


    for page in range(1,20):


        if page == 1:

            page_url = url

        else:

            page_url = (
                url
                +
                f"?sayfa={page}"
            )



        soup = fetch_page(
            page_url
        )


        if not soup:

            break



        before = len(products)



        for link in soup.find_all(
            "a",
            href=True
        ):


            href = link.get(
                "href"
            )



            if not href:
                continue



            if href.startswith("/"):

                href = (
                    BASE_URL
                    +
                    href
                )



            if href in PRODUCT_URL_CACHE:

                products.add(
                    href
                )



        if len(products) == before:

            break



    return products