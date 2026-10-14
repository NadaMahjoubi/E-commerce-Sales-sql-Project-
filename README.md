# E-commerce Sales Analytics (SQL + Python + Streamlit)

A project demonstrating relational database design, data quality validation, intermediate/advanced SQL, customer analytics, and an interactive dashboard.

> **Data note:** all data is synthetic and generated locally with a fixed random seed. Findings are demonstrations of the analysis workflow, not real-world business claims.

## Features
- SQLite schema with primary keys, foreign keys, `CHECK` constraints, and indexes.
- Reproducible synthetic data generation.
- Revenue KPIs consistently based on delivered orders and net line revenue after discounts.
- SQL analysis: monthly trends and growth, category and product performance, customer ranking, cancellation rate, cumulative revenue, and ratings.
- Customer RFM segmentation, cohort retention, and frequently-bought-together product pairs.
- Streamlit dashboard with date, country, and category filters.
- Automated data-quality tests.

## Setup
Use Python 3.10+.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

python -m pip install -r requirements.txt
python generate_data.py
pytest -q
streamlit run app.py
```

`generate_data.py` rebuilds `ecommerce.db` from scratch, then inserts data into the schema without replacing tables. Run it again to reset the synthetic dataset.

## Project structure
```text
ecommerce_sales_portfolio/
├── app.py
├── generate_data.py
├── schema.sql
├── requirements.txt
├── README.md
├── ecommerce.db              # generated locally
├── sql/
│   ├── sales_analysis.sql
│   ├── customer_segmentation.sql
│   └── data_quality.sql
└── tests/
    └── test_data_quality.py
```

## Metric definitions
- **Net line revenue:** `quantity * unit_price * (1 - discount_pct / 100)`.
- **Delivered revenue:** net line revenue for orders with status `delivered`.
- **Average order value:** delivered revenue divided by distinct delivered orders in the same filtered population.
- **Cancellation rate:** cancelled orders divided by all orders in the same country and period.
- Revenue excludes shipping, tax, refunds, and cost of goods because those fields are not part of this dataset.

## Suggested portfolio screenshots
1. Dashboard KPIs and monthly revenue.
2. Revenue by category and top products.
3. RFM customer segments.
4. ER diagram and a sample data-quality test result.

## Limitations and next steps
- Synthetic data is useful for demonstrating SQL but cannot establish actual market trends.
- The current cohort and basket analyses are exploratory; interpret small groups carefully.
- Potential extensions: add returns/refunds, shipping and tax, cost and margin, inventory snapshots, dbt models, CI checks, and deployment.
