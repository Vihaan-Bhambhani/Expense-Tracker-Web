import streamlit as st
import pandas as pd
import os
from datetime import datetime

CSV_FILE = 'expenses.csv'

def init_csv():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=['date', 'category', 'amount', 'description'])
        df.to_csv(CSV_FILE, index=False)

def add_expense(date, category, amount, description):
    new_expense = pd.DataFrame([{
        'date': date,
        'category': category,
        'amount': float(amount),
        'description': description
    }])
    new_expense.to_csv(CSV_FILE, mode='a', header=not os.path.exists(CSV_FILE), index=False)

def load_expenses():
    return pd.read_csv(CSV_FILE, parse_dates=['date'])

# Streamlit UI
st.title("💸 Personal Expense Tracker")

init_csv()

menu = ["Add Expense", "View Expenses", "Summary"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Add Expense":
    st.subheader("Add a New Expense")
    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", ["Food", "Transport", "Entertainment", "Utilities", "Other"])
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    description = st.text_input("Description")

    if st.button("Add"):
        add_expense(date, category, amount, description)
        st.success("Expense added!")

elif choice == "View Expenses":
    st.subheader("All Expenses")
    df = load_expenses()
    st.dataframe(df)

elif choice == "Summary":
    st.subheader("Summary Reports")
    df = load_expenses()
    
    if df.empty:
        st.warning("No expenses yet!")
    else:
        st.write("### Total Spent by Category")
        summary = df.groupby('category')['amount'].sum()
        st.bar_chart(summary)

        st.write("### Spending by Month")
        df['month'] = df['date'].dt.to_period('M').astype(str)
        monthly = df.groupby('month')['amount'].sum()
        st.line_chart(monthly)

        st.write("### Pie Chart of Category Spending")
        st.pyplot(summary.plot.pie(autopct='%1.1f%%').figure)
