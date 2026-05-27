import os
import pandas as pd
import psycopg2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    print("Connection successful")
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR PRIMARY KEY,
    customer_unique_id VARCHAR,
    customer_zip_code_prefix VARCHAR,
    customer_city VARCHAR,
    customer_state VARCHAR
);
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR PRIMARY KEY,
    customer_id VARCHAR,
    order_status VARCHAR,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id VARCHAR,
    order_item_id INTEGER,
    product_id VARCHAR,
    seller_id VARCHAR,
    shipping_limit_date TIMESTAMP,
    price DECIMAL,
    freight_value DECIMAL
);
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR PRIMARY KEY,
    product_category_name VARCHAR,
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER
);
CREATE TABLE IF NOT EXISTS sellers (
    seller_id VARCHAR PRIMARY KEY,
    seller_zip_code_prefix VARCHAR,
    seller_city VARCHAR,
    seller_state VARCHAR
);
CREATE TABLE IF NOT EXISTS order_payments (
    order_id VARCHAR,
    payment_sequential INTEGER,
    payment_type VARCHAR,
    payment_installments INTEGER,
    payment_value DECIMAL
);
CREATE TABLE IF NOT EXISTS order_reviews (
    review_id VARCHAR,
    order_id VARCHAR,
    review_score INTEGER,
    review_comment_title VARCHAR,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);
""")
conn.commit()
print("Tables created successfully")

def clean_value(val):
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    if isinstance(val, pd.Timestamp):
        if pd.isna(val):
            return None
        return val.to_pydatetime()
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    return val

def load_csv_to_table(csv_path, table_name, conn):
    df = pd.read_csv(csv_path)

    for col in df.columns:
        if 'date' in col.lower() or 'timestamp' in col.lower():
            df[col] = pd.to_datetime(df[col], errors='coerce')

    cursor = conn.cursor()
    cols = list(df.columns)
    for _, row in df.iterrows():
        values = [clean_value(val) for val in row]
        placeholders = ','.join(['%s'] * len(cols))
        col_names = ','.join(cols)
        query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        cursor.execute(query, values)
    conn.commit()
    print(f"Loaded {len(df)} rows into {table_name}")

data_path = "data"
load_csv_to_table(f"{data_path}/olist_customers_dataset.csv", "customers", conn)
load_csv_to_table(f"{data_path}/olist_orders_dataset.csv", "orders", conn)
load_csv_to_table(f"{data_path}/olist_order_items_dataset.csv", "order_items", conn)
load_csv_to_table(f"{data_path}/olist_products_dataset.csv", "products", conn)
load_csv_to_table(f"{data_path}/olist_sellers_dataset.csv", "sellers", conn)
load_csv_to_table(f"{data_path}/olist_order_payments_dataset.csv", "order_payments", conn)
load_csv_to_table(f"{data_path}/olist_order_reviews_dataset.csv", "order_reviews", conn)

cursor.close()
conn.close()
print("All data loaded successfully")