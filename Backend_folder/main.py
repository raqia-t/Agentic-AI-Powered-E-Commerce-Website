import subprocess
from fastapi import FastAPI
from pydantic import BaseModel
from agents_run import run_agents
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Configurable Fallback Messages ===
FALLBACK_MESSAGES = {
    "product": lambda query: (
        f"Sorry, we couldn’t find any products matching your request: \"{query}\". "
        "Please try a different search or adjust your filters."
    ),
    "order": (
        "Sorry, we couldn’t find any details for your order. "
        "Please make sure you’ve entered the correct order number."
    ),
    "support": (
        "Sorry, we couldn’t find any information for your request. "
        "Please provide more details so we can assist you better."
    ),
    "cart": {
        "message": "🛒 Your cart is empty or the action could not be completed.",
        "cart": [],
        "total": 0
    }
}

# === Models ===
class ChatRequest(BaseModel):
    query: str

# === Helper: Remove unwanted prefixes from LLM output ===
def clean_response(text: str) -> str:
    remove_prefixes = (
        "customer question:",
        "support response:",
        "here's a sample response:",
        "here's a polite and helpful",
    )
    lines = text.splitlines()
    cleaned = [
        line.strip()
        for line in lines
        if not any(line.strip().lower().startswith(p) for p in remove_prefixes)
    ]
    return " ".join(cleaned).strip()

# === Call LLaMA 3 safely ===
def llama_response(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return clean_response(result.stdout.strip())
    except Exception as e:
        print(f"LLaMA Error: {e}")
        return "Sorry, something went wrong while processing your request."

# === Chat Endpoint ===
@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    raw_result = run_agents(req.query)
    intent = raw_result.get("intent", "")

    payload = {
        "type": intent,
        "products": raw_result.get("products", []),
        "message": raw_result.get("message", ""),
        "order": None,
        "support": None,
        "cart": raw_result.get("cart", []),
        "search_query": req.query,
        "total": raw_result.get("total", 0)
    }

    # ================= PRODUCT INTENT =================
    if intent == "product":
        products_list = raw_result.get("products", [])
        if products_list:
            payload["message"] = llama_response(
                f"Answer naturally and briefly. "
                f"Recommend or describe these products in a clear way for this query: {req.query}. "
                f"Products: {products_list}"
            )
        else:
            payload["message"] = FALLBACK_MESSAGES["product"](req.query)

    # ================= CART INTENT =================
    elif intent == "cart":
        if payload["cart"]:
            payload["message"] = ""   # silent → no chatbot reply
        else:
            payload["message"] = FALLBACK_MESSAGES["cart"]["message"]

    # ================= ORDER INTENT =================
    elif intent == "order":
        payload["order"] = raw_result
        if raw_result:
            payload["message"] = llama_response(
                f"You are an order assistant for HappyCart. "
                f"Give a simple, clear update about this order info: {raw_result}. "
                f"Reply naturally without role labels or formal templates."
            )
        else:
            payload["message"] = FALLBACK_MESSAGES["order"]

    # ================= SUPPORT INTENT =================
    elif intent == "support":
        payload["support"] = raw_result
        if raw_result:
            payload["message"] = llama_response(
                f"You are a customer support assistant for HappyCart. "
                f"Answer the user’s question naturally and clearly based on this info: {raw_result}. "
                f"Do not include phrases like 'here’s a response'. Just reply directly."
            )
        else:
            payload["message"] = FALLBACK_MESSAGES["support"]

    # ================= UNKNOWN INTENT =================
    else:
        payload["type"] = "unknown"
        payload["message"] = (
            "Sorry, I’m not sure how to handle that request. "
            "Please try rephrasing or provide more details."
        )

    print("🔵 Backend Response:", payload)   # DEBUG
    return payload
