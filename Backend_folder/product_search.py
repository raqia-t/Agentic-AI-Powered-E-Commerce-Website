import faiss
import re
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
import json

# ===== DB Config =====
DB_CONFIG = {
    "dbname": "happycart",
    "user": "happyuser",
    "password": "happypass",
    "host": "localhost",
    "port": "5432"
}

# ===== Config =====
FAISS_INDEX_FILE = "embeddings/faiss_index.index"
ID_MAPPING_FILE = "embeddings/id_mapping.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CATEGORY_SYNONYMS = {
    "shoes": ["shoes", "sneakers", "joggers", "sandals"],
    "shirts": ["shirts", "t-shirts", "tees", "tshirt"],
    "jeans": ["jeans", "pants", "trousers"],
    "sunglasses": ["glasses", "sunglasses", "shades"]
}

COLOR_KEYWORDS = [
    "black", "white", "red", "blue", "green", "yellow", "pink", "grey", "gray", "orange", "purple", "brown"
]

GENDER_KEYWORDS = {
    "men": ["men", "men's", "male", "boy", "boys", "man"],
    "women": ["women", "women's", "female", "girl", "girls", "woman"],
    "unisex": ["unisex"]
}


class ProductSearchAgent:
    def __init__(self, faiss_index_file, id_mapping_file, embedding_model):
        # Load FAISS + embedder
        self.index = faiss.read_index(faiss_index_file)
        with open(id_mapping_file, "r", encoding="utf-8") as f:
            self.id_mapping = json.load(f)
        self.embedder = SentenceTransformer(embedding_model)

        # Load products from PostgreSQL
        self.products = self.load_products_from_db()

    def load_products_from_db(self):
        """Fetch all products from PostgreSQL into a dict {product_id: product_data}"""
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT product_id, title, description, price, category, image_url FROM products;")
        rows = cur.fetchall()
        conn.close()

        products = {}
        for r in rows:
            products[r[0]] = {
                "productID": r[0],
                "title": r[1],
                "description": r[2] if r[2] else "",
                "price": float(r[3]),
                "category": r[4],
                "image_url": r[5] if r[5] else "https://via.placeholder.com/200"
            }
        return products

    # ===== Detection Helpers =====
    def detect_category(self, query):
        query_lower = query.lower()
        for category, keywords in CATEGORY_SYNONYMS.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", query_lower) for kw in keywords):
                return category
        return None

    def detect_color(self, query):
        query_lower = query.lower()
        for color in COLOR_KEYWORDS:
            if re.search(rf"\b{color}\b", query_lower):
                return color
        return None

    def detect_gender_from_query(self, query):
        query_lower = query.lower()
        for gender, keywords in GENDER_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", query_lower) for kw in keywords):
                return gender
        return None

    def detect_gender_from_product(self, product):
        text = f"{product.get('title', '')} {product.get('description', '')}".lower()
        for gender, keywords in GENDER_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", text) for kw in keywords):
                return gender
        return None

    def detect_price_filter(self, query):
        query_lower = query.lower()
        match = re.search(r"(under|below|less than)\s*(\d+)", query_lower)
        if match:
            return ("lte", int(match.group(2)))
        match = re.search(r"(above|over|more than)\s*(\d+)", query_lower)
        if match:
            return ("gte", int(match.group(2)))
        if any(word in query_lower for word in ["lowest", "cheapest", "least"]):
            return ("min", None)
        if any(word in query_lower for word in ["highest", "most expensive", "costliest"]):
            return ("max", None)
        return None, None

    # ===== Core Search =====
    def search(self, query, top_k=5):
        category = self.detect_category(query)
        query_gender = self.detect_gender_from_query(query)
        price_dir, price_val = self.detect_price_filter(query)
        color = self.detect_color(query)

        print(f"\n🔍 Query: {query}")
        print(f"📂 Category filter: {category}")
        print(f"🧍 Gender filter from query: {query_gender}")
        print(f"🎨 Color filter: {color}")
        print(f"💰 Price filter: {price_dir} {price_val}")

        # ===== Step 1: DB Filtering =====
        filtered_products = []
        for pid, prod in self.products.items():
            if category and prod["category"].lower() != category:
                continue
            prod_gender = self.detect_gender_from_product(prod)
            if query_gender:
                if prod_gender and prod_gender.lower() != query_gender and prod_gender.lower() != "unisex":
                    continue
            if color and color.lower() not in prod["title"].lower() and color.lower() not in prod.get("description", "").lower():
                continue
            if price_dir == "lte" and prod["price"] > price_val:
                continue
            if price_dir == "gte" and prod["price"] < price_val:
                continue
            filtered_products.append(pid)

        if not filtered_products:
            print("❌ No related products found.")
            return []

        print(f"📦 Products after DB filtering: {len(filtered_products)}")

        # ===== Special Case: Lowest/Highest Price =====
        if price_dir in ["min", "max"]:
            sorted_products = sorted(
                filtered_products,
                key=lambda pid: self.products[pid]["price"],
                reverse=(price_dir == "max")
            )
            top_n = sorted_products[:3]
            return [self.products[pid] for pid in top_n]

        # ===== Step 2: FAISS Search =====
        subset_embeddings = []
        subset_ids = []
        for pid in filtered_products:
            try:
                idx = self.id_mapping.index(pid)
                subset_ids.append(idx)
                subset_embeddings.append(self.index.reconstruct(idx))
            except ValueError:
                continue

        if not subset_embeddings:
            print("❌ No embeddings found for filtered products.")
            return []

        subset_embeddings = np.array(subset_embeddings, dtype="float32")
        dim = subset_embeddings.shape[1]
        temp_index = faiss.IndexFlatL2(dim)
        temp_index.add(subset_embeddings)

        query_emb = self.embedder.encode([query]).astype("float32")
        scores, indices = temp_index.search(query_emb, min(top_k, len(subset_embeddings)))
        faiss_results = [self.id_mapping[subset_ids[idx]] for idx in indices[0]]

        # Return complete product objects including productID
        results = [self.products[pid] for pid in faiss_results]
        return results
