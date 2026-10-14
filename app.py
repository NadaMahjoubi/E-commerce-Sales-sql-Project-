from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ecommerce.db"

st.set_page_config(page_title="E-commerce Sales Analytics", page_icon="🛍️", layout="wide")
st.title(" E-commerce Sales Analytics")
st.caption("SQL-powered exploration of sales, product performance, and customer behavior.")
if not DB_PATH.exists():
    st.warning("Database not found. Run `python generate_data.py` first.")
    st.stop()

@st.cache_data
def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        orders = pd.read_sql_query("SELECT * FROM orders", conn, parse_dates=["order_date"])
        customers = pd.read_sql_query("SELECT * FROM customers", conn)
        products = pd.read_sql_query(
            """SELECT p.*, c.category_name FROM products p
               JOIN categories c USING(category_id)""", conn)
        lines = pd.read_sql_query(
            """SELECT o.order_id, o.customer_id, o.order_date, o.status,
                      oi.product_id, oi.quantity, oi.unit_price, oi.discount_pct,
                      oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0) AS line_revenue,
                      p.product_name, c.category_name
               FROM orders o
               JOIN order_items oi USING(order_id)
               JOIN products p USING(product_id)
               JOIN categories c USING(category_id)""", conn, parse_dates=["order_date"])
    return orders, customers, products, lines

orders, customers, products, lines = load_data()
min_date = orders["order_date"].min().date()
max_date = orders["order_date"].max().date()
with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Order date range", value=(min_date, max_date),
                               min_value=min_date, max_value=max_date)
    countries = sorted(customers["country"].dropna().unique().tolist())
    selected_countries = st.multiselect("Country", countries, default=countries)
    categories = sorted(products["category_name"].dropna().unique().tolist())
    selected_categories = st.multiselect("Category", categories, default=categories)
    st.caption("Revenue KPIs include delivered orders only, net of item discounts.")

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

customer_country = customers[["customer_id", "country"]]
filtered = lines[
    (lines["order_date"].dt.date >= start_date) &
    (lines["order_date"].dt.date <= end_date) &
    (lines["status"] == "delivered") &
    (lines["category_name"].isin(selected_categories))
].merge(customer_country, on="customer_id", how="left")
filtered = filtered[filtered["country"].isin(selected_countries)]
filtered_orders = orders[
    (orders["order_date"].dt.date >= start_date) &
    (orders["order_date"].dt.date <= end_date)
].merge(customer_country, on="customer_id", how="left")
filtered_orders = filtered_orders[filtered_orders["country"].isin(selected_countries)]

revenue = filtered["line_revenue"].sum()
order_count = filtered["order_id"].nunique()
aov = revenue / order_count if order_count else 0
customers_count = filtered["customer_id"].nunique()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Delivered revenue", f"${revenue:,.2f}")
k2.metric("Delivered orders", f"{order_count:,}")
k3.metric("Average order value", f"${aov:,.2f}")
k4.metric("Purchasing customers", f"{customers_count:,}")

left, right = st.columns(2)
with left:
    st.subheader("Monthly revenue")
    monthly = filtered.assign(month=filtered["order_date"].dt.to_period("M").astype(str))
    monthly = monthly.groupby("month", as_index=False)["line_revenue"].sum()
    if not monthly.empty:
        st.plotly_chart(px.line(monthly, x="month", y="line_revenue", markers=True,
                                labels={"month":"Month", "line_revenue":"Revenue"},
                                title="Delivered revenue over time"), use_container_width=True)
    else:
        st.info("No delivered sales match these filters.")
with right:
    st.subheader("Revenue by category")
    category = filtered.groupby("category_name", as_index=False)["line_revenue"].sum()
    if not category.empty:
        st.plotly_chart(px.bar(category.sort_values("line_revenue", ascending=False),
                               x="category_name", y="line_revenue",
                               labels={"category_name":"Category", "line_revenue":"Revenue"},
                               title="Net delivered revenue"), use_container_width=True)
    else:
        st.info("No category revenue to display.")

left, right = st.columns(2)
with left:
    st.subheader("Top products")
    top_products = (filtered.groupby(["product_name", "category_name"], as_index=False)
                    .agg(units_sold=("quantity", "sum"), revenue=("line_revenue", "sum"))
                    .sort_values("revenue", ascending=False).head(10))
    st.dataframe(top_products.round(2), use_container_width=True, hide_index=True)
with right:
    st.subheader("Order status")
    status_df = filtered_orders["status"].value_counts().rename_axis("status").reset_index(name="orders")
    if not status_df.empty:
        st.plotly_chart(px.pie(status_df, names="status", values="orders", hole=.45,
                               title="Orders in selected period and countries"),
                        use_container_width=True)

st.subheader("Customer RFM segmentation")
# Compute RFM for the dashboard using the same delivered-revenue definition.
with sqlite3.connect(DB_PATH) as conn:
    rfm = pd.read_sql_query("""
        WITH customer_orders AS (
          SELECT o.customer_id, o.order_id, o.order_date,
                 SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)) AS order_value
          FROM orders o JOIN order_items oi USING(order_id)
          WHERE o.status='delivered'
          GROUP BY o.customer_id, o.order_id, o.order_date
        ),
        metrics AS (
          SELECT c.customer_id, c.name,
                 CAST(julianday(date((SELECT MAX(order_date) FROM orders), '+1 day'))
                      - julianday(MAX(co.order_date)) AS INTEGER) AS recency_days,
                 COUNT(DISTINCT co.order_id) AS frequency,
                 ROUND(COALESCE(SUM(co.order_value),0),2) AS monetary_value
          FROM customers c LEFT JOIN customer_orders co USING(customer_id)
          GROUP BY c.customer_id, c.name
        )
        SELECT * FROM metrics WHERE frequency > 0
    """, conn)
if not rfm.empty:
    rfm["segment"] = "Needs Attention"
    rfm.loc[(rfm.recency_days <= rfm.recency_days.quantile(.2)) &
            (rfm.frequency >= rfm.frequency.quantile(.8)) &
            (rfm.monetary_value >= rfm.monetary_value.quantile(.8)), "segment"] = "Champions"
    rfm.loc[(rfm.recency_days > rfm.recency_days.quantile(.8)) &
            (rfm.frequency >= rfm.frequency.quantile(.6)), "segment"] = "At Risk"
    seg = rfm.groupby("segment", as_index=False).agg(
        customers=("customer_id", "count"), revenue=("monetary_value", "sum"))
    st.plotly_chart(px.bar(seg, x="segment", y="customers", color="segment",
                           title="Customers by RFM segment"), use_container_width=True)
    st.dataframe(rfm.sort_values("monetary_value", ascending=False).head(20),
                 use_container_width=True, hide_index=True)

st.subheader("Data notes")
st.markdown("""
- Dataset is synthetic and reproducible; it is not evidence of real company performance.
- Revenue means delivered-order line revenue after discounts; it excludes shipping, taxes, refunds, and cost of goods.
- The order-status chart counts orders independently of the category filter; category filters affect product/revenue metrics.
""")
