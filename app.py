import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

st.title("Personal Expense Tracker")

# Currency selection
currency_map = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥"
}
selected_currency = st.sidebar.selectbox("Select Currency", list(currency_map.keys()))
currency_symbol = currency_map[selected_currency]

# File to store data
DATA_FILE = 'expenses.csv'

# Load or create dataframe
if os.path.exists(DATA_FILE):
    try:
        df = pd.read_csv(DATA_FILE, parse_dates=['date'])
        if 'date' not in df.columns:
            raise ValueError("Missing 'date' column")
    except Exception as e:
        st.warning(f"CSV load issue: {e}. Creating fresh file.")
        df = pd.DataFrame(columns=['date', 'category', 'amount', 'description'])
        df.to_csv(DATA_FILE, index=False)
else:
    df = pd.DataFrame(columns=['date', 'category', 'amount', 'description'])
    df.to_csv(DATA_FILE, index=False)

# Add Expense
st.header("Add New Expense")
date = st.date_input("Date")
category = st.selectbox("Category", ["Food", "Transport", "Entertainment", "Utilities", "Other"])
amount = st.number_input(f"Amount ({currency_symbol})", min_value=0.0, format="%.2f")
description = st.text_input("Description")

if st.button("Add Expense"):
    new_expense = {'date': pd.to_datetime(date), 'category': category, 'amount': amount, 'description': description}
    df = pd.concat([df, pd.DataFrame([new_expense])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.success("Expense added!")

# View Expenses
st.header("View Expenses")
if not df.empty:
    df['amount_with_symbol'] = currency_symbol + df['amount'].round(2).astype(str)
    st.dataframe(df[['date', 'category', 'amount_with_symbol', 'description']])
else:
    st.info("No expenses yet. Add some!")

# Summary
st.header("Summary")
if not df.empty and 'date' in df.columns:
    try:
        df['month'] = df['date'].dt.to_period('M').astype(str)

        # Category summary
        cat_sum = df.groupby("category")["amount"].sum()
        st.write(f"### Total Spent by Category ({currency_symbol})")
        fig1, ax1 = plt.subplots()
        cat_sum.plot(kind='bar', ax=ax1)
        ax1.set_ylabel(f"Amount ({currency_symbol})")
        st.pyplot(fig1)

        # Pie chart
        fig2, ax2 = plt.subplots()
        cat_sum.plot(kind='pie', autopct='%1.1f%%', ax=ax2)
        ax2.set_ylabel("")
        ax2.set_title(f"Category Distribution ({currency_symbol})")
        st.pyplot(fig2)

        # Monthly summary
        month_sum = df.groupby('month')['amount'].sum()
        st.write(f"### Total Spent by Month ({currency_symbol})")
        fig3, ax3 = plt.subplots()
        month_sum.plot(kind='line', marker='o', ax=ax3)
        ax3.set_ylabel(f"Amount ({currency_symbol})")
        st.pyplot(fig3)
    except Exception as e:
        st.warning(f"Error generating summary: {e}")
else:
    st.info("No data for summary yet.")
