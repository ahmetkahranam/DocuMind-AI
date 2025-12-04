# chroma_docs.py
"""
Sadece embedded_data.json'u ChromaDB'ye ekler (docs klasöründeki dosyalar için).
"""
import os
import json
from chroma import ChromaDBManager
import logging

def main():
    INPUT_JSON = "embedded_data.json"
    if not os.path.exists(INPUT_JSON):
        print(f"[chroma_docs] {INPUT_JSON} yok.")
        return
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)
    
    chroma_manager = ChromaDBManager()
    
    logger.info(f"📄 JSON dosyası yükleniyor: {INPUT_JSON}")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not data:
        logger.warning(f"⚠️ JSON dosyası boş: {INPUT_JSON}")
        return
    
    logger.info(f"📊 {len(data)} doküman bulundu")
    
    # Batch import
    result = chroma_manager.add_documents_batch(
        data=data, batch_size=1000, skip_duplicates=True
    )
    
    logger.info("📊 IMPORT RAPORU:")
    logger.info(f"   İşlenen: {result['total_processed']}")
    logger.info(f"   Eklenen: {result['total_added']}")
    logger.info(f"   Atlanan: {result['skipped']}")
    logger.info(f"   Başarı oranı: {result['success_rate']:.1%}")
    
    print(f"[chroma_docs] {INPUT_JSON} ChromaDB'ye eklendi.")

if __name__ == "__main__":
    main()
