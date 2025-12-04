# base_docs.py
"""
Sadece docs klasöründeki dosyaları işler ve data.json olarak kaydeder.
"""
import os
import json
from base import AdvancedDocumentProcessor

def main():
    DOCS_FOLDER = "docs"
    OUTPUT_JSON = "data.json"
    if not os.path.exists(DOCS_FOLDER):
        print(f"[base_docs] {DOCS_FOLDER} klasörü yok.")
        return
    
    processor = AdvancedDocumentProcessor()
    data = processor.process_documents(DOCS_FOLDER)
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[base_docs] {OUTPUT_JSON} kaydedildi. {len(data)} dosya işlendi.")

if __name__ == "__main__":
    main()
