from app.database.product_repository import (
    get_all_products,
    search_products
)

products = get_all_products()

print("Toplam ürün:", len(products))

print("\nİlk 5 ürün:\n")

for product in products[:5]:
    print(product)

print("\n--- Arama Testi ---\n")

results = search_products("masa")

print("Bulunan:", len(results))

for product in results:
    print(product[2])