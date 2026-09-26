import json
import threading
import time

from app.database.connection import get_connection
from app.database.product_repository import insert_product
from app.services.site_search_service import get_product_urls, extract_product


SYNC_INTERVAL_SECONDS = 6 * 60 * 60

_sync_lock = threading.Lock()


def _normalize(url):
    return (url or "").strip().rstrip("/")


def _get_existing_state():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT url, product_card_id FROM products")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    urls = {_normalize(r[0]) for r in rows}

    ids = []
    for r in rows:
        try:
            ids.append(int(r[1]))
        except (TypeError, ValueError):
            pass

    return urls, (max(ids) if ids else -1)


def sync_new_products():
    """Sitemap'te olup veritabanında olmayan ürünleri ekler.

    Mevcut kayıtlara dokunmaz (tabloyu temizlemez), bu yüzden çalışırken
    arama/oylama kesintiye uğramaz. Aynı anda ikinci bir sync başlatılmaz.
    """
    if not _sync_lock.acquire(blocking=False):
        return {"status": "already_running"}

    try:
        site_urls = get_product_urls()
        existing_urls, max_id = _get_existing_state()

        missing = [u for u in site_urls if _normalize(u) not in existing_urls]

        added = 0
        failed = []

        for url in missing:
            try:
                product = extract_product(url)
                if not product:
                    failed.append(url)
                    continue

                max_id += 1

                insert_product({
                    "product_card_id": max_id,
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
                    ),
                })
                added += 1
            except Exception as exc:
                failed.append(url)
                print("Ürün eklenemedi:", url, exc)

        print("Ürün senkronu:", len(missing), "eksik,", added, "eklendi,", len(failed), "hata")

        return {
            "status": "done",
            "site_total": len(site_urls),
            "missing": len(missing),
            "added": added,
            "failed": failed,
        }
    finally:
        _sync_lock.release()


def start_auto_sync():
    """Sunucu açıldıktan sonra periyodik olarak yeni ürünleri içeri alır."""

    def loop():
        time.sleep(60)
        while True:
            try:
                sync_new_products()
            except Exception as exc:
                print("Otomatik ürün senkronu hatası:", exc)
            time.sleep(SYNC_INTERVAL_SECONDS)

    threading.Thread(target=loop, daemon=True).start()
