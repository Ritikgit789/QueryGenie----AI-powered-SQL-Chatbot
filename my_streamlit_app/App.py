import streamlit as st
import sqlite3
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv
import os
import pandas as pd
import re
import matplotlib.pyplot as plt

# Load API Key
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("❌ GOOGLE_API_KEY is missing! Please set it in a `.env` file.")
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Gemini LLM
llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)

# Apply Custom CSS for Styling
st.markdown(
    """
    <style>
        .stApp { background-color: #0f172a; color: white; }
        .stTextInput>div>div>input { font-size: 16px; padding: 10px; }
        .stButton>button { background-color: #4CAF50; color: white; font-size: 16px; padding: 10px 20px; }
        .stMarkdown { font-size: 18px; }
        .stSidebar { background-color: #1e293b; color: white; padding: 20px; }
        .stDataFrame { background-color: white; color: black; }
    </style>
    """,
    unsafe_allow_html=True
)

# Function to execute SQL query
def execute_sql_query(query):
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        return results, columns
    except Exception as e:
        conn.close()
        return str(e), []

# Function to clean AI-generated SQL
def clean_sql_query(sql_query):
    return re.sub(r"```sql|```", "", sql_query).strip()

# Function to generate SQL query from natural language
def generate_sql_query(user_input):
    prompt = f"""
    You are an AI SQL expert. Convert the following natural language question into an SQL query for an SQLite database.

    Database Schema:
    - Employees(ID, Name, Department, Salary, Hire_Date)
    - Departments(ID, Name, Manager)

    Rules:
    - The Employees table stores Department as TEXT, NOT an ID.
    - When querying employees by department, compare Department names, NOT Department IDs.
    - If asking for employees in the same department as someone, use:
      "SELECT Name FROM Employees WHERE Department = (SELECT Department FROM Employees WHERE Name = '<person_name>');"

    Question: {user_input}
    SQL Query (Only return the query, no explanation):
    """
    
    sql_query = llm.invoke(prompt)
    return clean_sql_query(sql_query)

# Function to fetch table data
def get_table_data(table_name):
    conn = sqlite3.connect("company.db")
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

# Function to show salary distribution
def show_salary_distribution():
    df = get_table_data("Employees")
    if df.empty:
        st.warning("⚠️ No employee data available.")
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    df.groupby("Department")["Salary"].mean().plot(kind="bar", ax=ax, color="skyblue")
    ax.set_title("💰 Average Salary by Department")
    ax.set_ylabel("Salary")
    st.pyplot(fig)

# Function to show employee count per department
def show_employee_count():
    df = get_table_data("Employees")
    if df.empty:
        st.warning("⚠️ No employee data available.")
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    df["Department"].value_counts().plot(kind="pie", autopct="%1.1f%%", startangle=90, ax=ax, cmap="viridis")
    ax.set_ylabel("")
    ax.set_title("👥 Employee Distribution by Department")
    st.pyplot(fig)

# Streamlit UI
st.title("💬 SQLSensei -- AI-Powered SQL Chatbot 🤖")
st.markdown("### Ask questions about the **company database**, and I'll generate and execute an SQL query!")

# Input Box
user_input = st.text_input("🔍 **Enter your query:**", "")

# Track query history
if "history" not in st.session_state:
    st.session_state.history = []

if st.button("⚡ Generate SQL & Query Database"):
    if user_input:
        sql_query = generate_sql_query(user_input)
        st.code(sql_query, language="sql")  # Show the SQL query

        results, columns = execute_sql_query(sql_query)
        if isinstance(results, str):
            st.error(f"❌ Error: {results}")  # Show error message if query fails
        else:
            if results:
                df = pd.DataFrame(results, columns=columns)
                st.dataframe(df)  # Display results in a table
            else:
                st.warning("⚠️ No results found.")
        
        # Store history
        st.session_state.history.append(user_input)

# Sidebar Options
st.sidebar.header("📊 **Database Insights**")

# Show Query History
if st.sidebar.checkbox("🕒 View Query History"):
    if st.session_state.history:
        st.sidebar.markdown("**Recent Queries:**")
        for query in st.session_state.history[-5:]:  # Show last 5 queries
            st.sidebar.markdown(f"✅ {query}")
    else:
        st.sidebar.warning("No queries yet.")

# View Table Data
st.sidebar.markdown("### 📂 **View Database Tables**")
table_choice = st.sidebar.selectbox("Choose a table", ["Employees", "Departments"])
if st.sidebar.button("🔍 Show Table Data"):
    df_table = get_table_data(table_choice)
    st.sidebar.write(f"**Showing `{table_choice}` Table:**")
    st.sidebar.dataframe(df_table)

# Data Visualizations
st.sidebar.markdown("### 📊 **Visualizations**")
if st.sidebar.button("💰 Show Salary Distribution"):
    show_salary_distribution()

if st.sidebar.button("👥 Show Employee Count by Department"):
    show_employee_count()
