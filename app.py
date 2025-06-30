import streamlit as st
import pandas as pd
import os
import plotly.express as px

st.set_page_config(page_title="Personal Expense Tracker", page_icon="💸", layout="wide")

st.markdown(
    "<h1 style='text-align: center; color: teal;'>💸 Personal Expense Tracker</h1>",
    unsafe_allow_html=True
)

# Helper functions
def load_user_data(username):
    filepath = f"{username.lower()}.csv"
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Currency", "Description"])

def save_user_data(username, data):
    data.to_csv(f"{username.lower()}.csv", index=False)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.df = pd.DataFrame()

# User login/registration
if not st.session_state.logged_in:
    st.subheader("👤 User Login / Registration")
    mode = st.radio("Select Mode:", ["New User", "Returning User"])
    username_input = st.text_input("Username:")

    if st.button("Proceed"):
        username = username_input.strip().lower()
        filepath = f"{username}.csv"

        if not username:
            st.warning("Please enter a username.")
        elif mode == "New User":
            if os.path.exists(filepath):
                st.error("Username already exists. Please choose a different one.")
            else:
                st.session_state.username = username
                st.session_state.df = load_user_data(username)
                st.session_state.logged_in = True
                st.success(f"✅ Welcome, {username_input}!")
        else:  # Returning User
            if not os.path.exists(filepath):
                st.error("Username not found. Please check or register as a new user.")
            else:
                st.session_state.username = username
                st.session_state.df = load_user_data(username)
                st.session_state.logged_in = True
                st.success(f"✅ Welcome back, {username_input}!")

    st.stop()

# Main app
if st.session_state.logged_in:
    username = st.session_state.username
    df = st.session_state.df

    st.sidebar.markdown(f"👋 **Logged in as:** `{username}`")
    menu = st.sidebar.radio("📌 Navigate", ["Add New Expense", "View Expenses", "Summary", "Currency Converter"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.df = pd.DataFrame()
        st.experimental_rerun()

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
                amount = st.number_input("Amount", min_value=0.0, format="%.2f")
                currency = st.selectbox("Currency", ["USD", "EUR", "INR", "GBP", "JPY"])

            description = st.text_input("Description (optional)")

            submitted = st.form_submit_button("Add Expense")
            if submitted:
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
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", df["Date"].min().date())
            with col2:
                end_date = st.date_input("End Date", df["Date"].max().date())

            filtered_df = df[(df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))]

            st.write(f"Showing expenses from **{start_date}** to **{end_date}**")
            st.dataframe(filtered_df)

            # Download button
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"{username}_expenses_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )

    elif menu == "Summary":
        st.header("📊 Summary")
        if df.empty:
            st.info("No expenses to summarize yet.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", df["Date"].min().date(), key="summary_start")
            with col2:
                end_date = st.date_input("End Date", df["Date"].max().date(), key="summary_end")

            filtered_df = df[(df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))]

            if filtered_df.empty:
                st.warning("No expenses in this date range.")
            else:
                st.subheader("💡 Total by Category")
                category_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index()
                st.dataframe(category_summary)

                fig_cat = px.pie(
                    category_summary,
                    names="Category",
                    values="Amount",
                    title="Expenses by Category",
                    hole=0.4
                )
                st.plotly_chart(fig_cat, use_container_width=True)

                st.subheader("💡 Total by Currency")
                currency_summary = filtered_df.groupby("Currency")["Amount"].sum().reset_index()
                st.dataframe(currency_summary)

                fig_cur = px.bar(
                    currency_summary,
                    x="Currency",
                    y="Amount",
                    title="Expenses by Currency",
                    color="Currency",
                    text_auto=True
                )
                st.plotly_chart(fig_cur, use_container_width=True)

                st.subheader("💡 Overall Spend")
                total_spend = filtered_df["Amount"].sum()
                st.success(f"💰 **Total Amount:** {total_spend:.2f} (Mixed currencies)")

    elif menu == "Currency Converter":
        st.header("💱 Currency Converter")

        # Example rates (these can be dynamic or user-input)
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
