import json
import re
from typing import Dict, Any, List, Optional


class OrderAgent:
    """
    Handles order-related queries: tracking, cancellation, confirmation.
    Works with an orders dataset in JSON format.
    """

    def __init__(self, orders_file: str):
        """
        orders_file: Path to a JSON file containing a list of orders.
        """
        with open(orders_file, "r", encoding="utf-8") as f:
            orders_list = json.load(f)

        # Create lookup dict keyed by order_id
        self.orders: Dict[str, Dict[str, Any]] = {
            order["order_id"]: order for order in orders_list
        }
        print(f"📦 Loaded {len(self.orders)} orders.")

    def _extract_order_id(self, query: str) -> Optional[str]:
        """
        Extract an order ID like 'ORD123' from the query.
        """
        match = re.search(r"\bORD\d+\b", query, re.IGNORECASE)
        if match:
            return match.group().upper()
        return None

    def _detect_action(self, query: str) -> str:
        """
        Determine whether the query is about tracking, canceling, or confirming.
        """
        q = query.lower()
        if any(word in q for word in ["cancel", "stop", "don't ship", "abort"]):
            return "cancel"
        elif any(word in q for word in ["deliver", "received", "mark as delivered", "got it"]):
            return "confirm"
        else:
            # Default action is tracking
            return "track"

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process the order query and return structured information.
        """
        order_id = self._extract_order_id(query)
        if not order_id:
            return {
                "intent": "order",
                "action": "unknown",
                "message": "❗ Please provide your Order ID (e.g., ORD123)."
            }

        order = self.orders.get(order_id)
        if not order:
            return {
                "intent": "order",
                "action": "unknown",
                "order_id": order_id,
                "error": f"❌ No order found with ID {order_id}."
            }

        action = self._detect_action(query)

        if action == "track":
            return {
                "intent": "order",
                "action": "track",
                "order_id": order_id,
                "status": order["status"],
                "eta": order["eta"],
                "items": order["items"]
            }

        elif action == "cancel":
            if order["status"].lower() in ["processing", "shipped"]:
                order["status"] = "canceled"
                return {
                    "intent": "order",
                    "action": "cancel",
                    "order_id": order_id,
                    "status": "canceled",
                    "message": f"✅ Order {order_id} has been canceled."
                }
            else:
                return {
                    "intent": "order",
                    "action": "cancel",
                    "order_id": order_id,
                    "status": order["status"],
                    "message": f"⚠️ Order {order_id} cannot be canceled as it is already {order['status']}."
                }

        elif action == "confirm":
            order["status"] = "delivered"
            return {
                "intent": "order",
                "action": "confirm",
                "order_id": order_id,
                "status": "delivered",
                "message": f"📦 Order {order_id} has been marked as delivered."
            }

        else:
            return {
                "intent": "order",
                "action": "unknown",
                "order_id": order_id,
                "message": "❓ Action not recognized."
            }


if __name__ == "__main__":
    # Example JSON file path
    ORDERS_FILE = "sample_orders.json"  # Replace with your file path
    agent = OrderAgent(ORDERS_FILE)

    while True:
        user_query = input("\nEnter your order query (or 'exit' to quit): ")
        if user_query.lower() == "exit":
            break

        result = agent.process_query(user_query)

        # Pretty print the response
        print("\n--- Order Agent Response ---")
        for key, value in result.items():
            print(f"{key.capitalize()}: {value}")
