from product_search import ProductSearchAgent
from customer_support import CustomerSupportAgent
from order_agent import OrderAgent
from cart_agent import CartAgent
from typing import Dict, Any
from langgraph.graph import StateGraph, END
import re

# ===== Config =====
FAQ_FILE = "faqs_and_policies.csv"
ORDERS_FILE = "sample_orders.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

FAISS_INDEX_FILE = "embeddings/faiss_index.index"
ID_MAPPING_FILE = "embeddings/id_mapping.json"

# ===== Initialize agents =====
product_agent = ProductSearchAgent(
    faiss_index_file=FAISS_INDEX_FILE,
    id_mapping_file=ID_MAPPING_FILE,
    embedding_model=EMBEDDING_MODEL
)

support_agent = CustomerSupportAgent(FAQ_FILE, EMBEDDING_MODEL)
order_agent = OrderAgent(ORDERS_FILE)
cart_agent = CartAgent(user_id="guest")


# ===== Controller Logic =====
def controller_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"].lower().strip()

    # ---- Cart Intents ----
    if ("add" in query and "cart" in query) or \
       ("remove" in query and "cart" in query) or \
       "view cart" in query or \
       "clear cart" in query:
        state["intent"] = "cart"

    # ---- Order Intents ----
    elif any(word in query for word in ["track", "cancel", "order", "deliver", "return"]):
        # ✅ Only trigger OrderAgent if Order ID present
        if re.search(r"\bord\d+\b", state["query"], re.IGNORECASE):
            state["intent"] = "order"
        else:
            state["intent"] = "support"

    # ---- Product Search Intents ----
    elif any(word in query for word in [
        "buy", "find", "show", "price", "sneakers", "shoes", "shirt",
        "jeans", "sunglasses", "tshirt"
    ]):
        state["intent"] = "product"

    # ---- Customer Support Intents ----
    else:
        state["intent"] = "support"

    return state


# ===== Agent Execution Functions =====
def run_cart(state: Dict[str, Any]) -> Dict[str, Any]:
    original_query = state["query"].strip()   # preserve case
    q = original_query.lower()                # lowercase for intent detection
    words = original_query.split()            # original words for productID

    productID = None
    for i, w in enumerate(words):
        if w.lower() == "productid" and i + 1 < len(words):
            productID = words[i + 1]   # keep case-sensitive (e.g. "P011")
            break

    result = {
        "message": "⚠️ Could not understand cart action.",
        "cart": [],
        "total": 0,
        "count": 0
    }

    if "add" in q and productID:
        result = cart_agent.add_to_cart(productID, quantity=1)
    elif "remove one" in q and productID:
        result = cart_agent.remove_one(productID)
    elif "remove" in q and productID:
        result = cart_agent.remove_from_cart(productID)
    elif "view" in q:
        result = cart_agent.view_cart()
    elif "clear" in q:
        result = cart_agent.clear_cart()

    state["result"] = result
    return state


def run_order(state: Dict[str, Any]) -> Dict[str, Any]:
    state["result"] = order_agent.process_query(state["query"])
    return state


def run_product(state: Dict[str, Any]) -> Dict[str, Any]:
    products = product_agent.search(state["query"])
    normalized = []
    for p in products:
        normalized.append({
            "productID": p.get("productID") or p.get("id") or p.get("product_id"),
            "title": p.get("title", ""),
            "description": p.get("description", ""),
            "price": p.get("price", 0),
            "image_url": p.get("image_url") or p.get("image", "")
        })
    state["result"] = normalized
    return state


def run_support(state: Dict[str, Any]) -> Dict[str, Any]:
    state["result"] = support_agent.search(state["query"])
    return state


# ===== LangGraph Workflow =====
workflow = StateGraph(dict)

workflow.add_node("controller", controller_agent)
workflow.add_node("cart", run_cart)
workflow.add_node("order", run_order)
workflow.add_node("product", run_product)
workflow.add_node("support", run_support)

workflow.add_conditional_edges(
    "controller",
    lambda state: state["intent"],
    {
        "cart": "cart",
        "order": "order",
        "product": "product",
        "support": "support",
    }
)

workflow.add_edge("cart", END)
workflow.add_edge("order", END)
workflow.add_edge("product", END)
workflow.add_edge("support", END)

workflow.set_entry_point("controller")
app = workflow.compile()


# ===== Run Agents (Main Entry) =====
def run_agents(query: str) -> Dict[str, Any]:
    final_state = app.invoke({"query": query})
    intent = final_state.get("intent", "unknown")
    result = final_state.get("result", {})

    response = {
        "type": intent,
        "intent": intent,
        "message": "",
        "cart": [],
        "total": 0,
        "count": 0,
        "products": []
    }

    if intent == "cart" and isinstance(result, dict):
        response["message"] = result.get("message", "")
        response["cart"] = result.get("cart", [])
        response["total"] = result.get("total", 0)
        response["count"] = result.get("count", 0)

    elif intent == "product" and isinstance(result, list):
        response["products"] = result
        response["message"] = "Here are some products you might like."

    elif intent == "order":
        response["message"] = str(result)

    elif intent == "support":
        response["message"] = str(result)

    else:
        response["message"] = "Sorry, I couldn’t understand your request."

    return response
