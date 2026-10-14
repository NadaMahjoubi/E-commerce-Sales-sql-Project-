-- RFM segmentation. The reference date is the day after the latest order date in the data,
-- which makes this query reproducible for synthetic historical datasets.
WITH delivered_orders AS (
    SELECT o.order_id, o.customer_id, o.order_date,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)) AS order_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY o.order_id, o.customer_id, o.order_date
),
reference_date AS (
    SELECT date(MAX(order_date), '+1 day') AS as_of_date FROM orders
),
rfm AS (
    SELECT c.customer_id, c.name,
           CAST(julianday((SELECT as_of_date FROM reference_date))
                - julianday(MAX(d.order_date)) AS INTEGER) AS recency_days,
           COUNT(DISTINCT d.order_id) AS frequency,
           ROUND(COALESCE(SUM(d.order_value), 0), 2) AS monetary_value
    FROM customers c
    LEFT JOIN delivered_orders d ON d.customer_id = c.customer_id
    GROUP BY c.customer_id, c.name
),
scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC) AS recency_score,
           NTILE(5) OVER (ORDER BY frequency ASC) AS frequency_score,
           NTILE(5) OVER (ORDER BY monetary_value ASC) AS monetary_score
    FROM rfm
    WHERE frequency > 0
)
SELECT customer_id, name, recency_days, frequency, monetary_value,
       recency_score, frequency_score, monetary_score,
       CASE
           WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4
               THEN 'Champions'
           WHEN recency_score >= 3 AND frequency_score >= 3
               THEN 'Loyal / Potential Loyalists'
           WHEN recency_score <= 2 AND frequency_score >= 3
               THEN 'At Risk'
           WHEN recency_score >= 4 AND frequency_score <= 2
               THEN 'Recent Customers'
           ELSE 'Needs Attention'
       END AS segment
FROM scored
ORDER BY monetary_value DESC;

-- Cohort retention by first delivered order month.
WITH first_purchase AS (
    SELECT customer_id, MIN(strftime('%Y-%m', order_date)) AS cohort_month
    FROM orders
    WHERE status = 'delivered'
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT customer_id, strftime('%Y-%m', order_date) AS activity_month
    FROM orders
    WHERE status = 'delivered'
),
cohort_activity AS (
    SELECT f.cohort_month, a.activity_month,
           (CAST(substr(a.activity_month, 1, 4) AS INTEGER)
              - CAST(substr(f.cohort_month, 1, 4) AS INTEGER)) * 12
           + (CAST(substr(a.activity_month, 6, 2) AS INTEGER)
              - CAST(substr(f.cohort_month, 6, 2) AS INTEGER)) AS month_number,
           COUNT(DISTINCT a.customer_id) AS active_customers
    FROM first_purchase f
    JOIN activity a ON a.customer_id = f.customer_id
    WHERE a.activity_month >= f.cohort_month
    GROUP BY f.cohort_month, a.activity_month
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM first_purchase
    GROUP BY cohort_month
)
SELECT ca.cohort_month, ca.activity_month, ca.month_number,
       cs.cohort_size, ca.active_customers,
       ROUND(100.0 * ca.active_customers / cs.cohort_size, 2) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON cs.cohort_month = ca.cohort_month
ORDER BY ca.cohort_month, ca.month_number;

-- Frequently bought together: pairs appearing in the same delivered order.
WITH order_products AS (
    SELECT DISTINCT o.order_id, oi.product_id
    FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'delivered'
)
SELECT p1.product_name AS product_a, p2.product_name AS product_b,
       COUNT(*) AS orders_together
FROM order_products a
JOIN order_products b ON a.order_id = b.order_id AND a.product_id < b.product_id
JOIN products p1 ON p1.product_id = a.product_id
JOIN products p2 ON p2.product_id = b.product_id
GROUP BY p1.product_id, p2.product_id
HAVING COUNT(*) >= 3
ORDER BY orders_together DESC
LIMIT 20;
