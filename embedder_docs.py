# embedder_docs.py
"""
Sadece data.json'u embedleyip embedded_data.json olarak kaydeder.
"""
import os
from embedder import process_documents_with_embeddings

def main():
    INPUT_JSON = "data.json"
    OUTPUT_JSON = "embedded_data.json"
    if not os.path.exists(INPUT_JSON):
        print(f"[embedder_docs] {INPUT_JSON} yok.")
        return
    process_documents_with_embeddings(INPUT_JSON, OUTPUT_JSON)
    print(f"[embedder_docs] {OUTPUT_JSON} kaydedildi.")

if __name__ == "__main__":
    main()
