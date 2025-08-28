import pandas as pd
import random
import json

# Load your Excel file (make sure the file path is correct)
df = pd.read_excel("products.xlsx")

# Mapping for singular/plural consistency
category_mapping = {
    "shoe": "shoes",
    "shoes": "shoes",
    "jean": "jeans",
    "jeans": "jeans",
    "shirt": "shirts",
    "shirts": "shirts",
    "sunglass": "sunglasses",
    "sunglasses": "sunglasses"
}

# Sample product titles and descriptions
sample_titles = {
    "shoes": ["Classic White Sneakers", "Running Sports Shoes", "Leather Formal Shoes"],
    "jeans": ["Slim Fit Blue Jeans", "Distressed Black Denim", "High Waist Skinny Jeans"],
    "shirts": ["Cotton Casual Shirt", "Formal White Shirt", "Plaid Flannel Shirt"],
    "sunglasses": ["Aviator Sunglasses", "Round Vintage Shades", "Sporty UV Sunglasses"]
}

sample_descriptions = {
    "shoes": "Comfortable and stylish footwear perfect for everyday wear.",
    "jeans": "Trendy and durable jeans designed for comfort and style.",
    "shirts": "High-quality shirts suitable for both casual and formal occasions.",
    "sunglasses": "UV-protected stylish sunglasses ideal for all seasons."
}

# Generate additional fields
def generate_product_data(row):
    raw_category = str(row.get('category', '')).strip().lower()
    category = category_mapping.get(raw_category, "shoes")  # fallback to 'shoes'
    row['category'] = category
    row['title'] = random.choice(sample_titles[category])
    row['description'] = sample_descriptions[category]
    row['price'] = random.randint(1500, 8000)  # price in PKR
    row['stock'] = random.randint(10, 100)
    return row

# Apply the data generation
df = df.apply(generate_product_data, axis=1)

# Rename for consistency if needed
df.rename(columns={'Image_url': 'image_url'}, inplace=True)

import pandas as pd
import random
import json

# Load your Excel file (make sure the file path is correct)
df = pd.read_excel("products.xlsx")

# Mapping for singular/plural consistency
category_mapping = {
    "shoe": "shoes",
    "shoes": "shoes",
    "jean": "jeans",
    "jeans": "jeans",
    "shirt": "shirts",
    "shirts": "shirts",
    "sunglass": "sunglasses",
    "sunglasses": "sunglasses"
}

# Sample product titles and descriptions
sample_titles = {
    "shoes": ["Classic White Sneakers", "Running Sports Shoes", "Leather Formal Shoes"],
    "jeans": ["Slim Fit Blue Jeans", "Distressed Black Denim", "High Waist Skinny Jeans"],
    "shirts": ["Cotton Casual Shirt", "Formal White Shirt", "Plaid Flannel Shirt"],
    "sunglasses": ["Aviator Sunglasses", "Round Vintage Shades", "Sporty UV Sunglasses"]
}

sample_descriptions = {
    "shoes": "Comfortable and stylish footwear perfect for everyday wear.",
    "jeans": "Trendy and durable jeans designed for comfort and style.",
    "shirts": "High-quality shirts suitable for both casual and formal occasions.",
    "sunglasses": "UV-protected stylish sunglasses ideal for all seasons."
}

# Generate additional fields
def generate_product_data(row):
    raw_category = str(row.get('category', '')).strip().lower()
    category = category_mapping.get(raw_category, "shoes")  
    row['category'] = category
    row['title'] = random.choice(sample_titles[category])
    row['description'] = sample_descriptions[category]
    row['price'] = random.randint(1500, 8000)
    row['stock'] = random.randint(10, 100)
    return row

# Apply the data generation
df = df.apply(generate_product_data, axis=1)

# Rename for consistency if needed
df.rename(columns={'Image_url': 'image_url'}, inplace=True)

# ✅ Fix URLs (remove \/ issue if present)
if 'image_url' in df.columns:
    df["image_url"] = df["image_url"].astype(str).str.replace("\\\\/", "/", regex=True)

# Reorder columns (keeping product_id from Excel)
cols = ['product_id', 'title', 'description', 'category', 'price', 'stock']
if 'image_url' in df.columns:
    cols.append('image_url')
df = df[cols]

# Save to JSON (clean way, no \/ escaping)
records = df.to_dict(orient="records")
with open("products.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print("✅ Files saved as products.json")

if 'image_url' in df.columns:
    df["image_url"] = df["image_url"].astype(str).str.replace("\\\\/", "/", regex=True)

# Reorder columns (keeping product_id from Excel)
cols = ['product_id', 'title', 'description', 'category', 'price', 'stock']
if 'image_url' in df.columns:
    cols.append('image_url')
df = df[cols]

# Save to JSON (clean way, no \/ escaping)
records = df.to_dict(orient="records")
with open("products.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print("✅ Files saved as products.json")
