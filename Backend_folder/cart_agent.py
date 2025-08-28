import psycopg2
from psycopg2.extras import RealDictCursor

# ===== DB Config =====
DB_CONFIG = {
    "dbname": "happycart",
    "user": "happyuser",
    "password": "happypass",
    "host": "localhost",
    "port": "5432"
}

class CartAgent:
    def __init__(self, user_id="guest"):
        self.user_id = user_id

    def _get_connection(self):
        return psycopg2.connect(**DB_CONFIG)

    def _fetch_cart(self):
        """Fetch full cart with details + total"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT c.product_id, p.title, p.description, p.price, p.image_url, c.quantity
                    FROM cart_items c
                    JOIN products p ON c.product_id = p.product_id
                    WHERE c.user_id = %s
                """, (self.user_id,))
                rows = cur.fetchall()

        cart_items, total_price = [], 0
        for row in rows:
            item_total = row["price"] * row["quantity"]
            total_price += item_total
            cart_items.append({
                "productID": row["product_id"],  # keep API field as productID for frontend
                "title": row["title"],
                "description": row["description"],
                "price": row["price"],
                "image_url": row["image_url"],
                "quantity": row["quantity"],
                "item_total": item_total
            })

        return cart_items, total_price

    def _make_response(self, message: str):
        """Standardized response with cart + total"""
        cart_items, total_price = self._fetch_cart()
        return {
            "message": message,
            "cart": cart_items,
            "total": total_price,
            "count": sum(item["quantity"] for item in cart_items)
        }

    # === Add to Cart ===
    def add_to_cart(self, productID, quantity=1):
        if quantity <= 0:
            return {"message": "⚠️ Quantity must be at least 1.", "cart": [], "total": 0, "count": 0}

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check product exists
                cur.execute("SELECT * FROM products WHERE product_id=%s", (productID,))
                product = cur.fetchone()
                if not product:
                    return {"message": f"❌ Product {productID} not found.", "cart": [], "total": 0, "count": 0}

                # Check if already in cart
                cur.execute(
                    "SELECT quantity FROM cart_items WHERE user_id=%s AND product_id=%s",
                    (self.user_id, productID)
                )
                row = cur.fetchone()

                if row:
                    cur.execute(
                        "UPDATE cart_items SET quantity = quantity + %s WHERE user_id=%s AND product_id=%s",
                        (quantity, self.user_id, productID)
                    )
                else:
                    cur.execute(
                        "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                        (self.user_id, productID, quantity)
                    )
            conn.commit()

        return self._make_response(f"✅ {product['title']} added to cart (Qty: {quantity}).")

    # === View Cart ===
    def view_cart(self):
        cart_items, total_price = self._fetch_cart()
        if not cart_items:
            return {"message": "🛒 Your cart is empty.", "cart": [], "total": 0, "count": 0}
        return self._make_response(f"🛒 You have {len(cart_items)} different products in your cart.")

    # === Remove Entire Product from Cart ===
    def remove_from_cart(self, productID):
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM cart_items WHERE user_id=%s AND product_id=%s", (self.user_id, productID))
                row = cur.fetchone()
                if not row:
                    return self._make_response(f"⚠️ Product {productID} is not in your cart.")

                cur.execute("DELETE FROM cart_items WHERE user_id=%s AND product_id=%s", (self.user_id, productID))
            conn.commit()

        return self._make_response(f"❌ Product {productID} removed from cart.")

    # === Remove One Quantity ===
    def remove_one(self, productID):
        """Decrease quantity by 1, remove item if quantity becomes 0"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT quantity FROM cart_items WHERE user_id=%s AND product_id=%s",
                            (self.user_id, productID))
                row = cur.fetchone()
                if not row:
                    return self._make_response(f"⚠️ Product {productID} is not in your cart.")

                if row["quantity"] > 1:
                    cur.execute("UPDATE cart_items SET quantity = quantity - 1 WHERE user_id=%s AND product_id=%s",
                                (self.user_id, productID))
                else:
                    cur.execute("DELETE FROM cart_items WHERE user_id=%s AND product_id=%s",
                                (self.user_id, productID))
            conn.commit()

        return self._make_response(f"➖ Removed one unit of product {productID}.")

    # === Clear Cart ===
    def clear_cart(self):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cart_items WHERE user_id=%s", (self.user_id,))
            conn.commit()
        return {"message": "🗑️ Cart cleared.", "cart": [], "total": 0, "count": 0}
