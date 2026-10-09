import os
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Expense Tracker & Spending Explorer", page_icon="💸", layout="wide")

st.markdown(
    "<h1 style='text-align: center; color: teal;'>💸 Personal Expense Tracker</h1>",
    unsafe_allow_html=True
)

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
    st.subheader("🧾 Open or Create an Expense Workspace")
    st.caption(
        "This app uses local CSV files keyed by workspace name. It has no password-based "
        "authentication, so use it locally with demo data—not for sensitive financial data on a shared server."
    )
    mode = st.radio("Workspace action", ["Create New Workspace", "Open Existing Workspace"])
    username_input = st.text_input("Workspace name", max_chars=24, help="3–24 letters, numbers, underscores, or hyphens.")

    if st.button("Continue"):
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
                st.session_state.logged_in = True
                st.rerun()

    st.stop()

# Main app
if st.session_state.logged_in:
    username = st.session_state.username
    df = st.session_state.df

    st.sidebar.markdown(f"👋 **Workspace:** `{username}`")
    menu = st.sidebar.radio("📌 Navigate", ["Add New Expense", "View Expenses", "Summary", "Currency Converter"])
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

        st.info("These are illustrative fixed rates for demonstrating conversion logic, not live exchange rates.")
        exchange_rates = {
            "USD": 1.0,
            "EUR": 0.92,
            "INR": 83.0,
            "GBP": 0.78,
            "JPY": 155.0
        }

        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount", min_value=0.0, format="%.2f")
            from_currency = st.selectbox("From Currency", list(exchange_rates.keys()))
        with col2:
            to_currency = st.selectbox("To Currency", list(exchange_rates.keys()))

        if st.button("Convert"):
            if from_currency == to_currency:
                st.info("Same currency selected. Amount unchanged.")
            else:
                # Convert to USD base, then to target
                amount_in_usd = amount / exchange_rates[from_currency]
                converted = amount_in_usd * exchange_rates[to_currency]
                st.success(f"{amount:.2f} {from_currency} = {converted:.2f} {to_currency}")
