# Expense Tracker & Spending Explorer

A lightweight **Python + Streamlit + pandas + Plotly** app for recording personal expenses and exploring spending patterns.

## Features

- Create and reopen a local CSV-backed workspace
- Record expenses with date, category, amount, currency, and description
- Filter expense records by date range and currency
- Export filtered expenses as CSV
- Summarize totals separately by currency
- Explore category composition and month-by-month spending for one selected currency
- Convert sample amounts using clearly labelled illustrative exchange rates

## Why currency-aware summaries matter

An amount in INR cannot be meaningfully added to an amount in USD without a conversion step. The app therefore keeps totals separate by currency and requires a currency selection for category and monthly-spend charts. It does not combine unlike currency amounts into one total.

## Tech stack

- Python
- Streamlit
- pandas
- Plotly

## Run locally

```bash
python -m venv .venv
```

Activate the environment:

**Windows**
```bash
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the requirements and start the app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Workspace CSV files are created alongside `app.py` and are excluded from version control.

## Data and security scope

Workspace names are file namespaces, **not passwords or secure authentication**. This is a local/demo application; do not use it as a shared public service or enter sensitive financial information when running it on a hosted server. A public multi-user deployment would require proper authentication and private durable storage.

The currency converter uses fixed illustrative rates, not live financial data. Verify exchange rates independently before relying on a conversion.

---
**Author:** Vihaan Bhambhani
