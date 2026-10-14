-- Each query should return zero rows (except the summary counts below).

-- Duplicate primary identifiers
SELECT customer_id, COUNT(*) AS n FROM customers GROUP BY customer_id HAVING COUNT(*) > 1;
SELECT product_id, COUNT(*) AS n FROM products GROUP BY product_id HAVING COUNT(*) > 1;
SELECT order_id, COUNT(*) AS n FROM orders GROUP BY order_id HAVING COUNT(*) > 1;
SELECT item_id, COUNT(*) AS n FROM order_items GROUP BY item_id HAVING COUNT(*) > 1;

-- Orphan references
SELECT o.order_id FROM orders o LEFT JOIN customers c ON c.customer_id=o.customer_id WHERE c.customer_id IS NULL;
SELECT oi.item_id FROM order_items oi LEFT JOIN orders o ON o.order_id=oi.order_id WHERE o.order_id IS NULL;
SELECT oi.item_id FROM order_items oi LEFT JOIN products p ON p.product_id=oi.product_id WHERE p.product_id IS NULL;

-- Invalid values
SELECT * FROM order_items WHERE quantity <= 0 OR unit_price < 0 OR discount_pct < 0 OR discount_pct > 100;
SELECT * FROM reviews WHERE rating NOT BETWEEN 1 AND 5;

-- Metric reconciliation: both values should match (within rounding tolerance).
SELECT
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS revenue_from_lines,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS reconciled_revenue
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
WHERE o.status='delivered';
