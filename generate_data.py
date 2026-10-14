"""Generate reproducible synthetic e-commerce data and load it into SQLite."""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ecommerce.db"
SEED = 42
random.seed(SEED)
Faker.seed(SEED)
fake = Faker()
TODAY = date.today()

CATEGORIES = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports", "Beauty"]
COUNTRIES = ["USA", "France", "Germany", "Tunisia", "UK"]

def make_data():
    customers = []
    for i in range(1, 501):
        registration = TODAY - timedelta(days=random.randint(30, 3 * 365))
        customers.append({
            "customer_id": i, "name": fake.name(),
            "email": f"customer{i}@example.com", "city": fake.city(),
            "country": random.choices(COUNTRIES, weights=[30, 20, 18, 17, 15])[0],
            "registration_date": registration.isoformat()
        })

    categories = [{"category_id": i, "category_name": name}
                  for i, name in enumerate(CATEGORIES, 1)]

    products = []
    for i in range(1, 201):
        category_id = random.randint(1, len(CATEGORIES))
        products.append({
            "product_id": i,
            "product_name": f"{fake.word().capitalize()} {random.choice(['Pro', 'Plus', 'Max', 'Lite'])} {i}",
            "category_id": category_id,
            "price": round(random.uniform(5, 500), 2),
            "stock": random.randint(0, 200)
        })

    orders = []
    for i in range(1, 1001):
        order_date = TODAY - timedelta(days=random.randint(0, 730))
        status = random.choices(
            ["delivered", "shipped", "pending", "cancelled"],
            weights=[62, 15, 10, 13]
        )[0]
        orders.append({
            "order_id": i,
            "customer_id": random.randint(1, 500),
            "order_date": order_date.isoformat(),
            "status": status
        })

    product_lookup = {p["product_id"]: p for p in products}
    order_items = []
    item_id = 1
    for order in orders:
        # Each order has 1–5 line items, with occasional repeated products prevented.
        chosen = random.sample(range(1, 201), random.randint(1, 5))
        for product_id in chosen:
            p = product_lookup[product_id]
            quantity = random.choices([1, 2, 3, 4, 5], weights=[40, 28, 16, 10, 6])[0]
            discount = random.choices([0, 5, 10, 15, 20], weights=[65, 12, 12, 7, 4])[0]
            order_items.append({
                "item_id": item_id, "order_id": order["order_id"],
                "product_id": product_id, "quantity": quantity,
                "unit_price": p["price"], "discount_pct": discount
            })
            item_id += 1

    # Reviews are tied to customers who purchased the reviewed product.
    order_customer = {o["order_id"]: o["customer_id"] for o in orders}
    purchase_pairs = set()
    for item in order_items:
        purchase_pairs.add((order_customer[item["order_id"]], item["product_id"]))
    reviews = []
    pairs = list(purchase_pairs)
    random.shuffle(pairs)
    for review_id, (customer_id, product_id) in enumerate(pairs[:800], 1):
        reviews.append({
            "review_id": review_id, "customer_id": customer_id,
            "product_id": product_id, "rating": random.choices([1,2,3,4,5], [4,7,14,35,40])[0],
            "review_date": (TODAY - timedelta(days=random.randint(0, 730))).isoformat()
        })
    return customers, categories, products, orders, order_items, reviews

def main():
    customers, categories, products, orders, order_items, reviews = make_data()
    if DB_PATH.exists():
        DB_PATH.unlink()  # Fresh deterministic rebuild; schema is recreated below.
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
        for table, rows in [
            ("customers", customers), ("categories", categories), ("products", products),
            ("orders", orders), ("order_items", order_items), ("reviews", reviews)
        ]:
            pd.DataFrame(rows).to_sql(table, conn, if_exists="append", index=False)
        conn.commit()
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign-key validation failed: {fk_errors[:5]}")
    print(f"Database created: {DB_PATH}")
    print(f"Customers={len(customers)}, products={len(products)}, orders={len(orders)}, "
          f"items={len(order_items)}, reviews={len(reviews)}")

if __name__ == "__main__":
    main()
