import pandas as pd
import faiss
import numpy as np
import re
from sentence_transformers import SentenceTransformer

# ===== Config =====
FAQ_FILE = "faqs_and_policies.csv"   # Updated UTF-8/Excel supported file
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  
TOP_K = 1  # Top match

class CustomerSupportAgent:
    def __init__(self, faq_file, embedding_model):
        # ---- Load Excel or CSV robustly ----
        try:
            if faq_file.endswith(".xlsx"):
                self.df = pd.read_excel(faq_file)
            else:
                # Auto-detect delimiter (comma, tab, semicolon)
                self.df = pd.read_csv(faq_file, encoding="utf-8-sig", sep=None, engine="python")
        except Exception as e:
            print(f"⚠️ UTF-8 failed: {e} → Retrying with latin1...")
            self.df = pd.read_csv(faq_file, encoding="latin1", sep=None, engine="python")

        # Normalize column names
        self.df.columns = [c.strip().lower() for c in self.df.columns]

        if not {"question", "answer"}.issubset(set(self.df.columns)):
            raise ValueError("CSV/Excel must have 'question' and 'answer' columns")

        # ---- Embedding setup ----
        self.embedder = SentenceTransformer(embedding_model)
        self.questions = self.df["question"].astype(str).tolist()
        self.answers = self.df["answer"].astype(str).tolist()
        print(f"📄 Loaded {len(self.questions)} FAQs/Policies")

        self.embeddings = self.embedder.encode(self.questions).astype("float32")

        # ---- FAISS index ----
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(self.embeddings)

    def search(self, query):
        print(f"\n💬 User Query: {query}")
        query_emb = self.embedder.encode([query]).astype("float32")
        scores, indices = self.index.search(query_emb, TOP_K)

        best_score = scores[0][0]
        best_idx = indices[0][0]

        if best_idx < 0 or best_score > 1.5:  # 1.5 is arbitrary threshold for poor matches
            print("❌ No relevant FAQ/Policy found.")
            return None

        best_q = self.questions[best_idx]
        best_a = self.answers[best_idx]
        print(f"✅ Matched FAQ: {best_q}")
        print(f"📜 Answer: {best_a}")
        return {"question": best_q, "answer": best_a}


if __name__ == "__main__":
    agent = CustomerSupportAgent(FAQ_FILE, EMBEDDING_MODEL)
    while True:
        q = input("\nAsk your question (or 'exit'): ")
        if q.lower() == "exit":
            break
        agent.search(q)
