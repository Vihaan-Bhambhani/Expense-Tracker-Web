import streamlit as st
import pandas as pd
import os

st.title("💸 Personal Expense Tracker")

# Helper functions
def load_user_data(username):
    filepath = f"{username}.csv"
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Currency", "Description"])

def save_user_data(username, data):
    data.to_csv(f"{username}.csv", index=False)

# USER MODE SELECTION
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.df = pd.DataFrame()

if not st.session_state.logged_in:
    mode = st.radio("Select Mode:", ["New User", "Returning User"])

    if mode == "New User":
        username = st.text_input("Create a username:")
        if st.button("Start"):
            filepath = f"{username}.csv"
            if not username:
                st.warning("Please enter a username.")
            elif os.path.exists(filepath):
                st.error("Username already exists. Please try a different one.")
            else:
                st.session_state.username = username
                st.session_state.df = load_user_data(username)
                st.session_state.logged_in = True
                st.success(f"Welcome, {username}!")
    else:  # Returning User
        username = st.text_input("Enter your username:")
        if st.button("Load Data"):
            filepath = f"{username}.csv"
            if not username:
                st.warning("Please enter your username.")
            elif not os.path.exists(filepath):
                st.error("Username not found. Please check or register as a new user.")
            else:
                st.session_state.username = username
                st.session_state.df = load_user_data(username)
                st.session_state.logged_in = True
                st.success(f"Welcome back, {username}!")

# MAIN APP ONCE LOGGED IN
if st.session_state.logged_in:
    # Sidebar navigation
    menu = st.sidebar.radio(
        "📌 Navigate",
        ["Add New Expense", "View Expenses", "Summary"]
    )

    df = st.session_state.df
    username = st.session_state.username

    if menu == "Add New Expense":
        st.header("➕ Add a New Expense")
        date = st.date_input("Date")
        category = st.selectbox("Category", ["Food", "Transport", "Entertainment", "Utilities", "Other"])
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        currency = st.selectbox("Currency", ["USD", "EUR", "INR", "GBP", "JPY"])
        description = st.text_input("Description")

        if st.button("Add Expense"):
            new_expense = {
                "Date": date,
                "Category": category,
                "Amount": amount,
                "Currency": currency,
                "Description": description
            }
            df = pd.concat([df, pd.DataFrame([new_expense])], ignore_index=True)
            save_user_data(username, df)
            st.session_state.df = df
            st.success("Expense added!")

    elif menu == "View Expenses":
        st.header("📄 Your Expenses")
        st.dataframe(df)

    elif menu == "Summary":
        st.header("📊 Summary")

        if df.empty:
            st.info("No expenses to summarize yet.")
        else:
            # Total by category
            st.subheader("Total by Category")
            category_summary = df.groupby("Category")["Amount"].sum().reset_index()
            st.dataframe(category_summary)

            # Total by currency
            st.subheader("Total by Currency")
            currency_summary = df.groupby("Currency")["Amount"].sum().reset_index()
            st.dataframe(currency_summary)

            # Show total spend
            st.subheader("Overall Spend")
            total_spend = df["Amount"].sum()
            st.write(f"💰 **Total Amount:** {total_spend:.2f} (Mixed currencies)")

    # Logout option
    if st.sidebar.button("🔓 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.df = pd.DataFrame()
        st.experimental_rerun()
