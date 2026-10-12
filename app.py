import os
import re
from pathlib import Path

import pandas as pd
import requests
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Expense Tracker & Spending Explorer", page_icon="💸", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1450px; }
    .hero-banner {
        background: linear-gradient(115deg, #5965d9 0%, #7540b7 55%, #9b45b3 100%);
        padding: 1.8rem 2rem; border-radius: 18px; color: #fff;
        margin-bottom: 1.4rem; box-shadow: 0 10px 28px rgba(72, 58, 145, .22);
    }
    .hero-banner .eyebrow { text-transform: uppercase; letter-spacing: .12em; font-size: .76rem; font-weight: 700; opacity: .85; }
    .hero-banner h1 { color: #fff; font-size: clamp(1.9rem, 3vw, 2.65rem); margin: .35rem 0 .55rem 0; }
    .hero-banner p { color: #f5f3ff; font-size: 1rem; margin: 0; opacity: .96; }
    .feature-panel {
        padding: 1.35rem; border: 1px solid rgba(145, 145, 170, .3);
        border-radius: 16px; background: rgba(125, 125, 150, .06); height: 100%;
    }
    .feature-panel h3 { margin-top: 0; }
    .feature-panel li { margin-bottom: .65rem; }
    .stButton > button, div[data-testid="stDownloadButton"] > button {
        border-radius: 10px; font-weight: 650; transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton > button:hover, div[data-testid="stDownloadButton"] > button:hover {
        transform: translateY(-1px); box-shadow: 0 5px 14px rgba(95, 75, 190, .18);
    }
    div[data-testid="stMetric"] {
        padding: .9rem 1rem; border: 1px solid rgba(145, 145, 170, .25);
        border-radius: 14px; background: rgba(125, 125, 150, .06);
    }
    div[data-testid="stMetricLabel"] { font-weight: 600; }
</style>
<div class="hero-banner">
    <div class="eyebrow">PERSONAL FINANCE · PYTHON · DATA EXPLORATION</div>
    <h1>💸 Expense Tracker & Spending Explorer</h1>
    <p>Record your expenses, understand category mix, and explore monthly spending trends.</p>
</div>
""", unsafe_allow_html=True)



@st.cache_data(ttl=3600, show_spinner=False)
def fetch_exchange_rates(base_currency: str) -> tuple[dict[str, float], str]:
    """Fetch latest published reference rates from Frankfurter (daily, not intraday)."""
    response = requests.get(
        "https://api.frankfurter.dev/v2/rates",
        params={"base": base_currency},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    rates = {base_currency: 1.0}
    rate_date = None
    for item in payload:
        quote = item.get("quote")
        rate = item.get("rate")
        if quote and isinstance(rate, (int, float)) and rate > 0:
            rates[quote] = float(rate)
            rate_date = max(rate_date or item.get("date", ""), item.get("date", ""))

    if len(rates) < 2:
        raise ValueError("The exchange-rate service returned no usable rates.")
    return rates, rate_date or "date not supplied"


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_supported_currencies() -> dict[str, str]:
    """Return currency codes and names supported by Frankfurter."""
    response = requests.get("https://api.frankfurter.dev/v2/currencies", timeout=10)
    response.raise_for_status()
    payload = response.json()
    return {
        item["iso_code"]: item.get("name", item["iso_code"])
        for item in payload
        if item.get("iso_code")
    }

# Local CSV storage. Workspace names are identifiers, not authentication.
BASE_DIR = Path(__file__).resolve().parent
DATA_COLUMNS = ["Date", "Category", "Amount", "Currency", "Description"]
USERNAME_PATTERN = re.compile(r"^[a-z0-9_-]{3,24}$")


def workspace_path(username: str) -> Path:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Workspace names must contain 3–24 letters, numbers, underscores, or hyphens.")
    return BASE_DIR / f"{username}.csv"


def load_user_data(username: str) -> pd.DataFrame:
    filepath = workspace_path(username)
    if not filepath.exists():
        return pd.DataFrame(columns=DATA_COLUMNS)

    data = pd.read_csv(filepath)
    for column in DATA_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NaT if column == "Date" else (0.0 if column == "Amount" else "")
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce")
    data = data.dropna(subset=["Date", "Amount"])
    data["Category"] = data["Category"].fillna("Other").astype(str)
    data["Currency"] = data["Currency"].fillna("INR").astype(str)
    data["Description"] = data["Description"].fillna("").astype(str)
    return data[DATA_COLUMNS]


def save_user_data(username: str, data: pd.DataFrame) -> None:
    filepath = workspace_path(username)
    data[DATA_COLUMNS].to_csv(filepath, index=False, date_format="%Y-%m-%d")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.df = pd.DataFrame()

# Workspace selection. A workspace name is not a password or a security boundary.
if not st.session_state.logged_in:
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.subheader("🧾 Open or create a workspace")
        st.caption("Keep a simple local record of expenses, then explore how your spending changes over time.")
        mode = st.radio("Workspace action", ["Create New Workspace", "Open Existing Workspace"])
        username_input = st.text_input(
            "Workspace name",
            max_chars=24,
            help="3–24 letters, numbers, underscores, or hyphens."
        )

        if st.button("Continue", type="primary", width="stretch"):
            username = username_input.strip().lower()
            if not USERNAME_PATTERN.fullmatch(username):
                st.warning("Use 3–24 letters, numbers, underscores, or hyphens for the workspace name.")
            else:
                filepath = workspace_path(username)
                if mode == "Create New Workspace" and filepath.exists():
                    st.error("That workspace already exists. Choose another name or open the existing workspace.")
                elif mode == "Open Existing Workspace" and not filepath.exists():
                    st.error("Workspace not found. Create a new workspace first.")
                else:
                    st.session_state.username = username
                    st.session_state.df = load_user_data(username)
                    if mode == "Create New Workspace":
                        # Persist even an empty workspace so it can be reopened after closing.
                        save_user_data(username, st.session_state.df)
                    st.session_state.logged_in = True
                    st.rerun()

    with right:
        st.markdown("""
        <div class="feature-panel">
            <h3>Make your spending easier to understand</h3>
            <ul>
                <li><b>Capture:</b> record a date, category, amount, currency, and note.</li>
                <li><b>Explore:</b> filter transactions and export the rows you need.</li>
                <li><b>Analyze:</b> compare category mix and monthly trends within a single currency.</li>
            </ul>
            <hr>
            <p><b>Demo scope</b></p>
            <p>This prototype uses CSV files named by workspace. It has no password-based authentication, so a workspace name is not private. Use synthetic/demo data only on the hosted app.</p>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# Main app
if st.session_state.logged_in:
    username = st.session_state.username
    df = st.session_state.df

    # Lightweight overview metrics; no combined total across unlike currencies.
    valid_dates = df["Date"].dropna() if not df.empty else pd.Series(dtype="datetime64[ns]")
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Transactions", f"{len(df):,}")
    metric2.metric("Categories used", f"{df['Category'].nunique():,}" if not df.empty else "0")
    metric3.metric("Currencies", f"{df['Currency'].nunique():,}" if not df.empty else "0")
    metric4.metric("Latest entry", valid_dates.max().strftime("%d %b %Y") if not valid_dates.empty else "—")
    st.markdown("")

    st.sidebar.markdown(f"👋 **Workspace:** `{username}`")
    menu = st.sidebar.radio("📌 Navigate", ["Summary", "Add New Expense", "View Expenses", "Currency Converter"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Close Workspace"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.df = pd.DataFrame()
        st.rerun()

    if menu == "Add New Expense":
        st.header("➕ Add a New Expense")
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date")
                category = st.selectbox(
                    "Category",
                    ["Food", "Transport", "Entertainment", "Utilities", "Investments", "Other"]
                )
            with col2:
                amount = st.number_input("Amount", min_value=0.01, step=1.0, format="%.2f")
                currency = st.selectbox("Currency", ["USD", "EUR", "INR", "GBP", "JPY"])

            description = st.text_input("Description (optional)")

            submitted = st.form_submit_button("Add Expense")
            if submitted and amount <= 0:
                st.warning("Expense amount must be greater than zero.")
            elif submitted:
                new_expense = {
                    "Date": pd.to_datetime(date),
                    "Category": category,
                    "Amount": amount,
                    "Currency": currency,
                    "Description": description
                }
                df = pd.concat([df, pd.DataFrame([new_expense])], ignore_index=True)
                save_user_data(username, df)
                st.session_state.df = df
                st.success("✅ Expense added successfully!")

    elif menu == "View Expenses":
        st.header("📄 View Expenses")
        if df.empty:
            st.info("No expenses recorded yet.")
        else:
            valid_dates = df["Date"].dropna()
            if valid_dates.empty:
                st.info("No valid dated expenses were found.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", valid_dates.min().date(), key="view_start")
                with col2:
                    end_date = st.date_input("End Date", valid_dates.max().date(), key="view_end")

                if start_date > end_date:
                    st.warning("Start Date must be on or before End Date.")
                else:
                    filtered_df = df[
                        (df["Date"] >= pd.Timestamp(start_date))
                        & (df["Date"] < pd.Timestamp(end_date) + pd.Timedelta(days=1))
                    ]
                    currencies = sorted(filtered_df["Currency"].dropna().unique().tolist())
                    currency_options = ["All currencies"] + currencies
                    selected_currency = st.selectbox("Currency filter", currency_options, key="view_currency")
                    if selected_currency != "All currencies":
                        filtered_df = filtered_df[filtered_df["Currency"] == selected_currency]

                    st.write(f"Showing expenses from **{start_date}** to **{end_date}**.")
                    st.dataframe(filtered_df, width="stretch", hide_index=True)

                    csv = filtered_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download filtered CSV",
                        data=csv,
                        file_name=f"{username}_expenses_{start_date}_to_{end_date}.csv",
                        mime="text/csv"
                    )

    elif menu == "Summary":
        st.header("📊 Spending Summary")
        if df.empty:
            st.info("No expenses to summarize yet.")
        else:
            valid_dates = df["Date"].dropna()
            if valid_dates.empty:
                st.info("No valid dated expenses were found.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", valid_dates.min().date(), key="summary_start")
                with col2:
                    end_date = st.date_input("End Date", valid_dates.max().date(), key="summary_end")

                if start_date > end_date:
                    st.warning("Start Date must be on or before End Date.")
                else:
                    date_filtered = df[
                        (df["Date"] >= pd.Timestamp(start_date))
                        & (df["Date"] < pd.Timestamp(end_date) + pd.Timedelta(days=1))
                    ]
                    if date_filtered.empty:
                        st.warning("No expenses in this date range.")
                    else:
                        st.subheader("💱 Totals by Currency")
                        currency_summary = (
                            date_filtered.groupby("Currency", as_index=False)["Amount"]
                            .sum()
                            .sort_values("Currency")
                        )
                        st.dataframe(currency_summary, width="stretch", hide_index=True)
                        st.caption("Amounts in different currencies are kept separate; they are not added into a misleading combined total.")

                        currencies = sorted(date_filtered["Currency"].dropna().unique().tolist())
                        selected_currency = st.selectbox("Currency for detailed analysis", currencies, key="summary_currency")
                        analysis_df = date_filtered[date_filtered["Currency"] == selected_currency]
                        total_spend = float(analysis_df["Amount"].sum())
                        st.metric(f"Total spend ({selected_currency})", f"{total_spend:,.2f}")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Spend by Category")
                            category_summary = (
                                analysis_df.groupby("Category", as_index=False)["Amount"]
                                .sum()
                                .sort_values("Amount", ascending=False)
                            )
                            st.dataframe(category_summary, width="stretch", hide_index=True)
                            fig_cat = px.pie(
                                category_summary,
                                names="Category",
                                values="Amount",
                                title=f"Expense Mix ({selected_currency})",
                                hole=0.4
                            )
                            st.plotly_chart(fig_cat, width="stretch")

                        with col2:
                            st.subheader("Monthly Spend Trend")
                            monthly_df = analysis_df.copy()
                            monthly_df["Month"] = monthly_df["Date"].dt.to_period("M").astype(str)
                            monthly_summary = (
                                monthly_df.groupby("Month", as_index=False)["Amount"]
                                .sum()
                                .sort_values("Month")
                            )
                            fig_month = px.line(
                                monthly_summary,
                                x="Month",
                                y="Amount",
                                markers=True,
                                title=f"Monthly Spend ({selected_currency})"
                            )
                            fig_month.update_layout(xaxis_title="Month", yaxis_title=f"Amount ({selected_currency})")
                            st.plotly_chart(fig_month, width="stretch")

    elif menu == "Currency Converter":
        st.header("💱 Currency Converter")
        st.caption("Live published reference rates · Frankfurter API · refreshed hourly while the app is active")

        try:
            currencies = fetch_supported_currencies()
        except (requests.RequestException, ValueError, KeyError) as exc:
            st.error("Could not load the supported currencies. Please retry when the rate service is available.")
            st.caption(f"Service detail: {type(exc).__name__}")
            st.stop()

        # Keep common currencies easy to find while exposing the full API-supported list.
        preferred = ["INR", "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "SGD"]
        currency_codes = [code for code in preferred if code in currencies]
        currency_codes += sorted(code for code in currencies if code not in currency_codes)

        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount", min_value=0.0, value=100.0, format="%.2f")
            from_currency = st.selectbox(
                "From Currency", currency_codes,
                index=currency_codes.index("INR") if "INR" in currency_codes else 0,
                format_func=lambda code: f"{code} — {currencies[code]}",
            )
        with col2:
            to_currency = st.selectbox(
                "To Currency", currency_codes,
                index=currency_codes.index("USD") if "USD" in currency_codes else min(1, len(currency_codes) - 1),
                format_func=lambda code: f"{code} — {currencies[code]}",
            )

        if st.button("Convert", type="primary"):
            if amount < 0:
                st.error("Enter an amount greater than or equal to zero.")
            elif from_currency == to_currency:
                st.success(f"{amount:,.2f} {from_currency} = {amount:,.2f} {to_currency}")
            else:
                try:
                    with st.spinner("Fetching the latest published reference rate…"):
                        rates, rate_date = fetch_exchange_rates(from_currency)
                    if to_currency not in rates:
                        st.error(f"No published rate is currently available for {from_currency} → {to_currency}.")
                    else:
                        converted = amount * rates[to_currency]
                        st.success(f"{amount:,.2f} {from_currency} = {converted:,.2f} {to_currency}")
                        st.caption(
                            f"Rate: 1 {from_currency} = {rates[to_currency]:,.6f} {to_currency} · "
                            f"Rate date: {rate_date}"
                        )
                except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                    st.error("Live rates are temporarily unavailable. Please try again shortly.")
                    st.caption(f"Service detail: {type(exc).__name__}")

        st.info(
            "Rates come from Frankfurter's published reference data and are cached for up to one hour. "
            "They update daily on working days, not in real time, and may differ from bank, card, or cash-exchange rates."
        )
