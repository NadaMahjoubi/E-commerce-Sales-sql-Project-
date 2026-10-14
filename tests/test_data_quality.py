import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "ecommerce.db"

def test_database_exists():
    assert DB_PATH.exists(), "Run `python generate_data.py` before tests."

def test_primary_keys_unique_and_non_null():
    with sqlite3.connect(DB_PATH) as conn:
        for table, key in [
            ("customers", "customer_id"), ("categories", "category_id"),
            ("products", "product_id"), ("orders", "order_id"),
            ("order_items", "item_id"), ("reviews", "review_id")
        ]:
            duplicates = conn.execute(
                f"SELECT {key} FROM {table} GROUP BY {key} HAVING COUNT(*) > 1"
            ).fetchall()
            nulls = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {key} IS NULL").fetchone()[0]
            assert not duplicates, f"Duplicate keys in {table}"
            assert nulls == 0, f"Null keys in {table}"

def test_foreign_keys_valid():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert errors == []

def test_business_rules():
    with sqlite3.connect(DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM order_items WHERE quantity <= 0").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM order_items WHERE unit_price < 0").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM order_items WHERE discount_pct NOT BETWEEN 0 AND 100").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM reviews WHERE rating NOT BETWEEN 1 AND 5").fetchone()[0] == 0

def test_delivered_revenue_nonnegative():
    with sqlite3.connect(DB_PATH) as conn:
        revenue = conn.execute("""
            SELECT SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0))
            FROM orders o JOIN order_items oi USING(order_id)
            WHERE o.status = 'delivered'
        """).fetchone()[0] or 0
        assert revenue >= 0
