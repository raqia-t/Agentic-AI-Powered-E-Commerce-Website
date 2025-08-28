import json
import pandas as pd
import faiss
import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np
import os

# === CONFIGURATION ===
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
PRODUCTS_PATH = "products.json"
FAQ_PATH = "faqs_and_policies.csv"
EMBEDDINGS_DIR = "embeddings"
FAISS_INDEX_PATH = os.path.join(EMBEDDINGS_DIR, "faiss_index.index")
ID_MAPPING_PATH = os.path.join(EMBEDDINGS_DIR, "id_mapping.json")

# PostgreSQL credentials
DB_CONFIG = {
    "dbname": "happycart",
    "user": "happyuser",
    "password": "happypass",
    "host": "localhost",
    "port": "5432"
}

# === STEP 2: EMBEDDING GENERATION ===
print("[Step 2] Generating Embeddings...")

# Load product data
with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
    products = json.load(f)

# Load FAQ/Policy data (handle encoding issues)
try:
    faq_df = pd.read_csv(FAQ_PATH, encoding="utf-8")
except UnicodeDecodeError:
    faq_df = pd.read_csv(FAQ_PATH, encoding="latin1")

faq_df['content'] = faq_df['question'] + " " + faq_df['answer']  # Merge Q & A

# Load embedding model
model = SentenceTransformer(EMBED_MODEL)

# Prepare product texts
product_texts = [p['title'] + " " + p['description'] for p in products]
product_ids = [p['product_id'] for p in products]  # FIX: changed from productID → product_id

# Prepare FAQ texts
faq_texts = faq_df['content'].tolist()
faq_ids = faq_df['id'].astype(str).tolist()

# Combine products + FAQs
all_texts = product_texts + faq_texts
all_ids = product_ids + faq_ids

# Generate embeddings
embeddings = model.encode(all_texts, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

# Create output directory
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

# Save embeddings and ID mapping
np.save(os.path.join(EMBEDDINGS_DIR, "embeddings.npy"), embeddings)
with open(ID_MAPPING_PATH, "w", encoding="utf-8") as f:
    json.dump(all_ids, f, ensure_ascii=False, indent=2)

print("✅ Embeddings and ID mapping saved.")

# === STEP 3: VECTOR STORE SETUP WITH FAISS ===
print("[Step 3] Setting up FAISS index...")

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

faiss.write_index(index, FAISS_INDEX_PATH)

print(f"✅ FAISS index saved at: {FAISS_INDEX_PATH}")

# === STEP 4: POSTGRESQL PRODUCT & CART DATABASE SETUP ===
print("[Step 4] Inserting product data into PostgreSQL...")

create_products_table = """
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR PRIMARY KEY,
    title TEXT,
    description TEXT,
    category TEXT,
    price INT,
    stock INT,
    image_url TEXT
);
"""

create_cart_table = """
CREATE TABLE IF NOT EXISTS cart_items (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    product_id VARCHAR REFERENCES products(product_id),
    quantity INT DEFAULT 1
);
"""

insert_product_query = """
INSERT INTO products (product_id, title, description, category, price, stock, image_url)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (product_id) DO NOTHING;
"""

# Connect to DB
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Create tables
    cur.execute(create_products_table)
    cur.execute(create_cart_table)
    conn.commit()

    # Insert products
    for p in products:
        cur.execute(insert_product_query, (
            p['product_id'],  # FIXED key
            p['title'],
            p['description'],
            p['category'],
            p['price'],
            p['stock'],
            p['image_url']
        ))

    conn.commit()
    print("✅ Products & Cart tables ready, products inserted successfully.")

except Exception as e:
    print("❌ Error during DB insertion:", e)
finally:
    if 'cur' in locals(): cur.close()
    if 'conn' in locals(): conn.close()
