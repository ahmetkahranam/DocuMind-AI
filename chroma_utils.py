from chroma import ChromaDBManager

def remove_from_chromadb(filename):
    """Dosyayı ChromaDB'den kaldırır"""
    try:
        chroma_manager = ChromaDBManager()
        chroma_manager._initialize_client()
        if not chroma_manager.collection:
            print("ChromaDB koleksiyonu başlatılamadı, silme atlandı.")
            return

        before_count = chroma_manager.collection.count()
        print(f"[ChromaDB] Silme öncesi toplam chunk: {before_count}")
        print(f"[ChromaDB][DEBUG] Silinmek istenen dosya adı: {filename}")
        try:
            sample = chroma_manager.collection.get(limit=20, include=["metadatas"])
            all_sources = [m.get('source_file') for m in sample.get('metadatas',[]) if m and 'source_file' in m]
            print(f"[ChromaDB][DEBUG] İlk 20 chunk'ın source_file alanları: {all_sources}")
        except Exception as e:
            print(f"[ChromaDB][DEBUG] source_file örnekleri alınamadı: {e}")

        # Önce tam eşleşme ile sil
        where_eq = {"source_file": {"$eq": filename}}
        results_eq = chroma_manager.collection.get(where=where_eq, include=["metadatas"])
        silinen = 0
        if results_eq and results_eq.get("ids"):
            print(f"[ChromaDB] Tam eşleşme ile silinecek {len(results_eq['ids'])} chunk bulundu.")
            chroma_manager.collection.delete(ids=results_eq["ids"])
            silinen += len(results_eq["ids"])
        else:
            print(f"[ChromaDB] Tam eşleşme ile chunk bulunamadı, startswith ile denenecek.")
            # startswith ile sil (eski veriler için)
            where_sw = {"source_file": {"$contains": filename}}
            results_sw = chroma_manager.collection.get(where=where_sw, include=["ids","metadatas"])
            if results_sw and results_sw.get("ids"):
                print(f"[ChromaDB] StartsWith/Contains ile silinecek {len(results_sw['ids'])} chunk bulundu.")
                chroma_manager.collection.delete(ids=results_sw["ids"])
                silinen += len(results_sw["ids"])
            else:
                print(f"[ChromaDB] UYARI: {filename} için hiçbir chunk bulunamadı!")

        after_count = chroma_manager.collection.count()
        print(f"[ChromaDB] Silme sonrası toplam chunk: {after_count} (Silinen: {silinen})")

    except Exception as e:
        print(f"ChromaDB'den silme hatası: {e}")
