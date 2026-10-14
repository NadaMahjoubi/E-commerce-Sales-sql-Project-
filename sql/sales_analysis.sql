-- All monetary metrics use delivered orders and net line revenue after discount.
-- Revenue = quantity * unit_price * (1 - discount_pct / 100).

-- 1. Core KPIs
SELECT
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS delivered_revenue,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    ROUND(
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0))
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 2
    ) AS average_order_value,
    COUNT(DISTINCT o.customer_id) AS purchasing_customers
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status = 'delivered';

-- 2. Monthly revenue and month-over-month growth
WITH monthly AS (
    SELECT strftime('%Y-%m', o.order_date) AS month,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY strftime('%Y-%m', o.order_date)
),
with_previous AS (
    SELECT month, revenue,
           LAG(revenue) OVER (ORDER BY month) AS previous_month_revenue
    FROM monthly
)
SELECT month, ROUND(revenue, 2) AS revenue,
       ROUND(100.0 * (revenue - previous_month_revenue)
             / NULLIF(previous_month_revenue, 0), 2) AS mom_growth_pct
FROM with_previous
ORDER BY month;

-- 3. Revenue by category
SELECT c.category_name,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS revenue,
       SUM(oi.quantity) AS units_sold
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
JOIN categories c ON c.category_id = p.category_id
WHERE o.status = 'delivered'
GROUP BY c.category_id, c.category_name
ORDER BY revenue DESC;

-- 4. Best-selling products (delivered orders only)
SELECT p.product_id, p.product_name, c.category_name,
       SUM(oi.quantity) AS units_sold,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
JOIN categories c ON c.category_id = p.category_id
WHERE o.status = 'delivered'
GROUP BY p.product_id, p.product_name, c.category_name
ORDER BY units_sold DESC, revenue DESC
LIMIT 10;

-- 5. Cancellation rate by country (denominator = all orders)
SELECT c.country, COUNT(*) AS total_orders,
       SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
       ROUND(100.0 * SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 2) AS cancellation_rate_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.country
ORDER BY cancellation_rate_pct DESC;

-- 6. Customer spending rank (outer ORDER BY ensures deterministic top 20)
WITH customer_spend AS (
    SELECT c.customer_id, c.name, c.country,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)) AS total_spent
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY c.customer_id, c.name, c.country
)
SELECT customer_id, name, country, ROUND(total_spent, 2) AS total_spent,
       DENSE_RANK() OVER (ORDER BY total_spent DESC) AS spending_rank
FROM customer_spend
ORDER BY total_spent DESC, customer_id
LIMIT 20;

-- 7. Products with low stock
SELECT product_id, product_name, stock
FROM products
WHERE stock < 10
ORDER BY stock, product_name;

-- 8. Average product rating; products with at least 3 reviews
SELECT p.product_id, p.product_name,
       ROUND(AVG(r.rating), 2) AS avg_rating,
       COUNT(r.review_id) AS review_count
FROM products p
JOIN reviews r ON r.product_id = p.product_id
GROUP BY p.product_id, p.product_name
HAVING COUNT(r.review_id) >= 3
ORDER BY avg_rating DESC, review_count DESC;

-- 9. Customers who never placed an order
SELECT c.customer_id, c.name, c.email
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;

-- 10. Cumulative delivered revenue
WITH monthly AS (
    SELECT strftime('%Y-%m', o.order_date) AS month,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)) AS revenue
    FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY strftime('%Y-%m', o.order_date)
)
SELECT month, ROUND(revenue, 2) AS monthly_revenue,
       ROUND(SUM(revenue) OVER (ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2)
       AS cumulative_revenue
FROM monthly ORDER BY month;
