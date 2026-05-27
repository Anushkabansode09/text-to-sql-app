import os
import re
import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Page config
st.set_page_config(
    page_title="Text-to-SQL | Olist Analytics",
    page_icon="🛒",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# Get schema info
@st.cache_data
def get_schema():
    schema = """
    TABLE: customers
    COLUMNS: customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state

    TABLE: orders
    COLUMNS: order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at,
             order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date

    TABLE: order_items
    COLUMNS: order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value

    TABLE: products
    COLUMNS: product_id, product_category_name, product_name_lenght, product_description_lenght,
             product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm

    TABLE: sellers
    COLUMNS: seller_id, seller_zip_code_prefix, seller_city, seller_state

    TABLE: order_payments
    COLUMNS: order_id, payment_sequential, payment_type, payment_installments, payment_value

    TABLE: order_reviews
    COLUMNS: review_id, order_id, review_score, review_comment_title, review_comment_message,
             review_creation_date, review_answer_timestamp

    RELATIONSHIPS:
    - orders.customer_id = customers.customer_id
    - order_items.order_id = orders.order_id
    - order_items.product_id = products.product_id
    - order_items.seller_id = sellers.seller_id
    - order_payments.order_id = orders.order_id
    - order_reviews.order_id = orders.order_id
    """
    return schema

# LLM setup
@st.cache_resource
def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )

# Prompt template
def get_prompt():
    template = """
You are an expert PostgreSQL analyst working with the Olist Brazilian E-Commerce database.

DATABASE SCHEMA:
{schema}

RULES:
1. Generate ONLY a valid PostgreSQL SELECT query
2. Do NOT include any explanation, markdown, or code blocks
3. Do NOT use ```sql or ``` tags
4. Use table aliases for readability
5. Always use LIMIT 100 unless user asks for specific number
6. For date operations use PostgreSQL syntax
7. Return ONLY the raw SQL query

USER QUESTION: {question}

SQL QUERY:
"""
    return PromptTemplate(template=template, input_variables=["schema", "question"])

# Generate SQL
def generate_sql(question, llm, schema):
    prompt = get_prompt()
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"schema": schema, "question": question})
    sql = response.strip()
    sql = re.sub(r'```sql|```', '', sql).strip()
    return sql

# Execute SQL
def execute_query(sql, conn):
    try:
        conn.rollback()
        df = pd.read_sql_query(sql, conn)
        return df, None
    except Exception as e:
        conn.rollback()
        return None, str(e)

# Retry with error context
def retry_sql(question, sql, error, llm, schema):
    retry_template = """
You are an expert PostgreSQL analyst. Your previous SQL query had an error.

DATABASE SCHEMA:
{schema}

ORIGINAL QUESTION: {question}
FAILED SQL: {sql}
ERROR: {error}

Fix the SQL query. Return ONLY the corrected raw SQL query with no explanation or markdown.

CORRECTED SQL:
"""
    retry_prompt = PromptTemplate(
        template=retry_template,
        input_variables=["schema", "question", "sql", "error"]
    )
    chain = retry_prompt | llm | StrOutputParser()
    response = chain.invoke({"schema": schema, "question": question, "sql": sql, "error": error})
    sql = response.strip()
    sql = re.sub(r'```sql|```', '', sql).strip()
    return sql

# Main UI
def main():
    st.title("🛒 Olist E-Commerce Text-to-SQL")
    st.markdown("Ask questions about the Olist dataset in plain English.")

    # Sidebar
    with st.sidebar:
        st.header("📊 Sample Questions")
        sample_questions = [
            "What are the top 10 product categories by revenue?",
            "How many orders were delivered late?",
            "Which cities have the most customers?",
            "What is the average review score by product category?",
            "Which sellers have the highest average order value?",
            "What is the monthly revenue trend in 2017?",
            "What percentage of payments are made by credit card?",
            "Which states have the most orders?"
        ]
        for q in sample_questions:
            if st.button(q, key=q):
                st.session_state.question = q

        st.divider()
        st.header("🗄️ Schema")
        st.code("""
customers
orders
order_items
products
sellers
order_payments
order_reviews
        """)

    # Query history
    if "history" not in st.session_state:
        st.session_state.history = []

    # Input
    question = st.text_input(
        "Ask a question about the data:",
        value=st.session_state.get("question", ""),
        placeholder="e.g. What are the top 5 selling product categories?"
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        run_button = st.button("▶ Run Query", type="primary")
    with col2:
        clear_button = st.button("🗑 Clear History")

    if clear_button:
        st.session_state.history = []
        st.rerun()

    if run_button and question:
        conn = get_connection()
        llm = get_llm()
        schema = get_schema()

        with st.spinner("Generating SQL..."):
            sql = generate_sql(question, llm, schema)

        st.subheader("Generated SQL")
        st.code(sql, language="sql")

        with st.spinner("Executing query..."):
            df, error = execute_query(sql, conn)

        # Retry on error
        if error:
            st.warning("First attempt failed. Retrying with error context...")
            with st.spinner("Retrying..."):
                sql = retry_sql(question, sql, error, llm, schema)
                st.subheader("Corrected SQL")
                st.code(sql, language="sql")
                df, error = execute_query(sql, conn)

        if error:
            st.error(f"Query failed: {error}")
        else:
            st.success(f"✅ {len(df)} rows returned")
            st.subheader("Results")
            st.dataframe(df, use_container_width=True)

            # Auto chart for numeric results
            numeric_cols = df.select_dtypes(include='number').columns.tolist()
            if len(df) > 1 and len(numeric_cols) >= 1:
                st.subheader("📈 Chart")
                non_numeric = df.select_dtypes(exclude='number').columns.tolist()
                if non_numeric:
                    st.bar_chart(df.set_index(non_numeric[0])[numeric_cols[0]])

            # Save to history
            st.session_state.history.append({
                "question": question,
                "sql": sql,
                "rows": len(df)
            })

    # Query history display
    if st.session_state.history:
        st.divider()
        st.subheader("📜 Query History")
        for i, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"Q: {item['question']} ({item['rows']} rows)"):
                st.code(item['sql'], language="sql")

if __name__ == "__main__":
    main()