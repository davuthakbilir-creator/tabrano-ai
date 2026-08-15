from app.services.product_service import find_products

products = find_products("bahçe")

print(f"Bulunan ürün: {len(products)}\n")

for product in products:
    print(product[2])