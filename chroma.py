import os
import json
import shutil
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import numpy as np
from config import config
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Performans optimizasyonlu ChromaDB yönetim sınıfı"""

    def __init__(
        self, chroma_path: str = "./chroma", collection_name: str = "rag_documents"
    ):
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._stats_cache = None
        self._stats_cache_time = None
        self._cache_ttl = 300  # 5 dakika cache
        self._lock = threading.RLock()
        
        # Connection pooling için
        self._connection_pool = []
        self._pool_size = 3
        
        self.stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "unique_sources": 0,
            "index_size_mb": 0,
            "last_updated": None,
        }

        self._initialize_client()

    def _initialize_client(self):
        """Yeni ChromaDB client konfigürasyonu ile başlatma"""
        try:
            # Eğer chroma dizini bozuksa, yeniden oluştur
            if os.path.exists(self.chroma_path):
                try:
                    # Test amaçlı client oluştur - YENİ YÖNTEM
                    test_client = chromadb.PersistentClient(path=self.chroma_path)
                    test_client.list_collections()
                    test_client = None  # Memory'den temizle
                except Exception as e:
                    logger.warning(f"ChromaDB dizini bozuk, yeniden oluşturuluyor: {e}")
                    shutil.rmtree(self.chroma_path)

            # ChromaDB dizinini oluştur
            os.makedirs(self.chroma_path, exist_ok=True)

            # YENİ ChromaDB client konfigürasyonu (deprecated settings kaldırıldı)
            self.client = chromadb.PersistentClient(path=self.chroma_path)

            # Local embedding function tanımla
            from embedder import LocalEmbedder
            
            def embedding_function(texts):
                embedder = LocalEmbedder(model=config.EMBEDDING_MODEL)
                if isinstance(texts, str):
                    texts = [texts]
                embeddings = []
                for text in texts:
                    embedding = embedder.embed_single(text)
                    embeddings.append(embedding.tolist())
                return embeddings
            
            # Custom embedding function class
            class LocalEmbeddingFunction:
                def __call__(self, input):
                    return embedding_function(input)

            # Collection oluştur/al - Local embedding function ile
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=LocalEmbeddingFunction(),
                    metadata={
                        "hnsw:space": "cosine",
                        "description": "RAG documents collection with local embeddings"
                    },
                )
            
            # Dimension uyumluluğunu kontrol et
            self._validate_collection_dimension()

            logger.info(f"✅ ChromaDB başlatıldı (yeni konfigürasyon): {self.chroma_path}")
            self._update_stats()

        except Exception as e:
            logger.error(f"❌ ChromaDB başlatma hatası: {e}")
            raise

    def _validate_collection_dimension(self):
        """Optimize edilmiş dimension validation"""
        try:
            if not self.collection:
                return

            count = self.collection.count()
            if count == 0:
                print(f"✅ Yeni collection, dimension: {config.EMBEDDING_DIMENSION}")
                return

            sample = self.collection.get(limit=1, include=["embeddings"])

            # Ensure sample["embeddings"] exists and is a non-empty structure
            embeddings = sample.get("embeddings")
            
              # Check if embeddings is not None or empty
                # If embeddings is a numpy array or list-like, handle both cases
            if hasattr(embeddings, '__len__'):  # This checks for any object with a length (like list, numpy array, etc.)
                if len(embeddings) > 0:
                    actual_dim = len(embeddings[0])  # Assuming embeddings[0] is a list or array
                    expected_dim = config.EMBEDDING_DIMENSION

                    if actual_dim != expected_dim:
                        print(f"❌ DIMENSION MISMATCH! Collection: {actual_dim}, Config: {expected_dim}")
                        raise ValueError(f"Embedding dimension mismatch: {actual_dim} != {expected_dim}")
                    else:
                        print(f"✅ Dimension validation passed: {actual_dim}")
                else:
                    print("⚠️ Embeddings is an empty list or array.")
            else:
                print("⚠️ Embeddings is not a list or array-like object.")
            

        except Exception as e:
            print(f"⚠️ Dimension validation hatası: {e}")



    @lru_cache(maxsize=128)
    def _get_directory_size_cached(self, path: str) -> float:
        """Cache'li dizin boyutu hesaplama"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.warning(f"Dizin boyutu hesaplama hatası: {e}")
        return total_size / (1024 * 1024)

    def _update_stats(self):
        """Optimize edilmiş istatistik güncelleme"""
        try:
            with self._lock:
                now = datetime.now()
                
                # Cache kontrolü
                if (self._stats_cache_time and 
                    (now - self._stats_cache_time).total_seconds() < self._cache_ttl):
                    self.stats = self._stats_cache.copy()
                    return
                
                if not self.collection:
                    logger.warning("ChromaDB collection None, istatistik güncellenemedi.")
                    return
                    
                count = self.collection.count()
                self.stats["total_chunks"] = count
                self.stats["last_updated"] = now.isoformat()

                # Dosya boyutu - cache'li
                if os.path.exists(self.chroma_path):
                    self.stats["index_size_mb"] = self._get_directory_size_cached(self.chroma_path)

                # Unique sources - sample-based estimation
                if count > 0:
                    # Büyük collection'lar için sampling
                    sample_size = min(count, 500)  # Daha az sample
                    sample_metadata = self.collection.get(
                        limit=sample_size, 
                        include=["metadatas"]
                    )
                    if sample_metadata and sample_metadata.get("metadatas"):
                        sources = set()
                        for metadata in sample_metadata["metadatas"] or []:
                            if metadata and "source_file" in metadata:
                                sources.add(metadata["source_file"])
                        
                        # Estimation for large collections
                        if sample_size < count:
                            estimated_sources = len(sources) * (count / sample_size)
                            self.stats["unique_sources"] = int(estimated_sources)
                        else:
                            self.stats["unique_sources"] = len(sources)
                
                # Cache güncelle
                self._stats_cache = self.stats.copy()
                self._stats_cache_time = now
                
        except Exception as e:
            logger.warning(f"İstatistik güncelleme hatası: {e}")

    def check_duplicates(self, new_ids: List[str]) -> Dict[str, Any]:
        """Optimize edilmiş duplicate kontrolü"""
        try:
            if not self.collection:
                return {"error": "collection is None"}
                
            # Büyük collection'larda duplicate kontrolü çok yavaş
            total_count = self.collection.count()
            
            # Eğer collection çok büyükse, duplicate kontrolü atla
            if total_count > 50000:  # 50k'dan fazlaysa
                logger.info(f"⚠️ Büyük collection ({total_count}), duplicate kontrolü atlanıyor")
                return {
                    "total_existing": total_count,
                    "new_ids_count": len(new_ids),
                    "duplicates": [],
                    "duplicate_count": 0,
                    "skipped_large_collection": True
                }
            
            # Batch'li duplicate kontrolü
            existing_ids = set()
            batch_size = 2000  # Daha büyük batch
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                for offset in range(0, total_count, batch_size):
                    future = executor.submit(
                        self._get_ids_batch, 
                        offset, 
                        min(batch_size, total_count - offset)
                    )
                    futures.append(future)
                
                for future in as_completed(futures):
                    try:
                        batch_ids = future.result()
                        existing_ids.update(batch_ids)
                    except Exception as e:
                        logger.warning(f"Batch duplicate kontrolü hatası: {e}")
            
            duplicates = [id for id in new_ids if id in existing_ids]
            
            return {
                "total_existing": len(existing_ids),
                "new_ids_count": len(new_ids),
                "duplicates": duplicates,
                "duplicate_count": len(duplicates),
            }
            
        except Exception as e:
            logger.error(f"❌ Duplicate kontrol hatası: {e}")
            return {"error": str(e)}

    def _get_ids_batch(self, offset: int, limit: int) -> List[str]:
        """Batch halinde ID'leri getir"""
        try:
            batch = self.collection.get(
                limit=limit,
                offset=offset,
                include=["ids"]
            )
            return batch.get("ids", []) if batch else []
        except Exception as e:
            logger.warning(f"ID batch getirme hatası: {e}")
            return []

    def add_documents_batch(
        self,
        data: List[Dict[str, Any]],
        batch_size: int = 2000,  # Daha büyük batch
        skip_duplicates: bool = False,  # Default false (hızlandırma)
    ) -> Dict[str, Any]:
        """Optimize edilmiş batch doküman ekleme"""

        logger.info("🚀 Optimize edilmiş batch doküman ekleme başlıyor...")

        if not self.collection:
            print("❌ Collection None, ekleme yapılamıyor")
            return {"total_added": 0, "skipped": 0, "errors": ["collection is None"]}

        # Verileri parallel işle
        with ThreadPoolExecutor(max_workers=4) as executor:
            future = executor.submit(self._process_data_batch, data)
            ids, embeddings, metadatas, documents = future.result()

        total_chunks = len(ids)
        if total_chunks == 0:
            logger.warning("⚠️ Eklenecek chunk bulunamadı")
            return {"total_added": 0, "skipped": 0, "errors": []}

        logger.info(f"📊 Toplam {total_chunks} chunk işlenecek")

        # Conditional duplicate kontrolü
        duplicate_info = {"duplicates": [], "duplicate_count": 0}
        if skip_duplicates:
            logger.info("🔍 Duplicate kontrol yapılıyor...")
            duplicate_info = self.check_duplicates(ids)

            # Büyük collection'da duplicate kontrolü atlandıysa
            if duplicate_info.get("skipped_large_collection"):
                logger.info("⚠️ Büyük collection, duplicate kontrolü atlandı")
            elif duplicate_info.get("duplicate_count", 0) > 0:
                logger.info(f"⚠️ {duplicate_info['duplicate_count']} duplicate bulundu")
                # Duplicate filtering logic...

        # Optimize edilmiş batch ekleme
        total_added = 0
        errors = []

        print(f"⚡ {len(ids)} chunk ChromaDB'ye eklenecek (batch size: {batch_size})")

        # Parallel batch processing
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            
            for i in range(0, len(ids), batch_size):
                end = min(i + batch_size, len(ids))
                future = executor.submit(
                    self._add_batch_chunk,
                    ids[i:end],
                    embeddings[i:end],
                    metadatas[i:end],
                    documents[i:end],
                    i // batch_size + 1,
                    (len(ids) + batch_size - 1) // batch_size
                )
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    batch_result = future.result()
                    total_added += batch_result["added"]
                    if batch_result["error"]:
                        errors.append(batch_result["error"])
                except Exception as e:
                    print(f"❌ Batch işleme hatası: {e}")
                    errors.append(f"Batch processing error: {e}")

        # Cache temizle
        self._stats_cache = None
        self._update_stats()

        result = {
            "total_processed": total_chunks,
            "total_added": total_added,
            "skipped": duplicate_info.get("duplicate_count", 0),
            "errors": errors,
            "success_rate": total_added / total_chunks if total_chunks > 0 else 0,
        }

        print("✅ Optimize edilmiş batch ekleme tamamlandı")
        return result

    def _add_batch_chunk(
        self, 
        ids: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]], 
        documents: List[str],
        batch_num: int,
        total_batches: int
    ) -> Dict[str, Any]:
        """Tek batch'i ekle"""
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
            
            batch_size = len(ids)
            logger.info(f"📦 Batch {batch_num}/{total_batches}: {batch_size} chunk eklendi")
            
            return {"added": batch_size, "error": None}
            
        except Exception as e:
            error_msg = f"Batch {batch_num} hatası: {e}"
            logger.error(f"❌ {error_msg}")
            return {"added": 0, "error": error_msg}

    def _process_data_batch(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[List[float]], List[Dict[str, Any]], List[str]]:
        """Optimize edilmiş veri batch işleme"""
        ids, embeddings, metadatas, documents = [], [], [], []

        print("İşlem başlatıldı")
        print(f"Toplam {len(data)} öğe işlenecek.")
        
        for idx, item in enumerate(data):
            print(f"İşleniyor ({idx + 1}/{len(data)}): {item}")

            filename = item.get("filename", "unknown")
            file_type = item.get("file_type", "unknown")
            chunks = item.get("chunks", [])
            chunk_embeddings = item.get("embeddings", [])
            doc_metadata = item.get("document_metadata", {})

            print(f"  Filename: {filename}")
            print(f"  File type: {file_type}")
            print(f"  Chunk sayısı: {len(chunks)}")
            print(f"  Embedding sayısı: {len(chunk_embeddings)}")
            print(f"  Document metadata: {doc_metadata}")

            # Hızlı validation
            min_count = min(len(chunks), len(chunk_embeddings))
            print(f"  Min chunk ve embedding sayısı: {min_count}")
            
            if min_count == 0:
                print("  ⚠️ Boş chunk veya embedding bulundu, atlanıyor")
                continue

            # Vectorized operations
            for idx in range(min_count):
                chunk = chunks[idx]
                if not chunk or not chunk.strip():
                    print(f"  ⚠️ Boş veya sadece boşluklardan oluşan chunk atlanıyor: {chunk}")
                    continue

                embedding = chunk_embeddings[idx]
                if len(embedding) != config.EMBEDDING_DIMENSION:
                    print(f"⚠️ Geçersiz embedding boyutu bulundu: {len(embedding)} (Beklenen: {config.EMBEDDING_DIMENSION}), chunk: {chunk}")
                    continue

                if not embedding or len(embedding) != config.EMBEDDING_DIMENSION:
                    print(f"  ⚠️ Geçersiz embedding bulundu, atlanıyor: {embedding}")
                    continue

                # Optimize edilmiş ID generation
                unique_id = f"{filename}_{idx}_{len(chunk)}"
                print(f"  Oluşturulan unique_id: {unique_id}")

                # Minimal metadata
                metadata = {
                    "source_file": filename,
                    "file_type": file_type,
                    "chunk_index": idx,
                    "chunk_length": len(chunk),
                }

                print(f"  Meta verisi: {metadata}")

                # Sadece gerekli doc metadata ekle
                if doc_metadata:
                    for key in ["title", "author", "created_date"]:  # Sadece önemli alanlar
                        if key in doc_metadata and doc_metadata[key]:
                            metadata[f"doc_{key}"] = str(doc_metadata[key])
                            print(f"  Eklendi doc_metadata: {key} -> {doc_metadata[key]}")

                ids.append(unique_id)
                embeddings.append(embedding)
                metadatas.append(metadata)
                documents.append(chunk)

                print(f"  Veriler eklendi - ID: {unique_id}, Chunk length: {len(chunk)}")

        # İşlem sonrasında verileri print ile yazdır
        print(f"\nİşlem tamamlandı:")
        print(f"Toplam chunk sayısı: {len(ids)}")
        print(f"Toplam embedding sayısı: {len(embeddings)}")
        print(f"Toplam metadata sayısı: {len(metadatas)}")
        print(f"Toplam document sayısı: {len(documents)}")

        # Ayrıca, her listeyi tek tek de print ile yazdırabilirsin
        print(f"Örnek IDs: {ids[:1]}")  # İlk 1 ID
        print(f"Örnek Embeddings: {embeddings[:1]}")  # İlk 1 embedding
        print(f"Örnek Metadatas: {metadatas[:1]}")  # İlk 1 metadata
        print(f"Örnek Documents: {documents[:1]}")  # İlk 1 document

        return ids, embeddings, metadatas, documents

    def search_similar(
        self,
        query_embedding: List[float],
        n_results: int = 10,  # Daha az default
        filters: Optional[Dict[str, Any]] = None,
        include_distances: bool = True,
    ) -> Dict[str, Any]:
        """Optimize edilmiş similarity search"""
        try:
            if not self.collection:
                return self._empty_search_result()

            # Optimize edilmiş include fields
            include_fields = ["documents", "metadatas"]
            if include_distances:
                include_fields.append("distances")

            # Where clause
            where_clause = None
            if filters:
                where_clause = self._build_where_clause(filters)

            # Search with timeout protection
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=include_fields,
                    where=where_clause,
                )
            except Exception as e:
                logger.warning(f"Search timeout/error, retry with smaller n_results: {e}")
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, 5),  # Fallback
                    include=["documents", "metadatas"],
                )

            if not results:
                return self._empty_search_result()

            docs = results.get("documents", [[]])
            return {
                "documents": docs,
                "metadatas": results.get("metadatas", [[]]),
                "distances": results.get("distances", [[]]) if include_distances else [[]],
                "total_found": len(docs[0]) if docs and docs[0] else 0,
            }
            
        except Exception as e:
            logger.error(f"❌ Search hatası: {e}")
            return self._empty_search_result()

    def _empty_search_result(self) -> Dict[str, Any]:
        """Boş search result"""
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "total_found": 0,
        }

    def _build_where_clause(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Optimize edilmiş filter clause building"""
        if not filters:
            return None
            
        where = {}
        
        # Sık kullanılan filtreleri optimize et
        if "source_files" in filters and isinstance(filters["source_files"], list):
            if len(filters["source_files"]) == 1:
                where["source_file"] = {"$eq": filters["source_files"][0]}
            else:
                where["source_file"] = {"$in": filters["source_files"]}
        
        if "file_types" in filters and isinstance(filters["file_types"], list):
            if len(filters["file_types"]) == 1:
                where["file_type"] = {"$eq": filters["file_types"][0]}
            else:
                where["file_type"] = {"$in": filters["file_types"]}
        
        # Diğer filtreler
        for key, value in filters.items():
            if key in ["source_files", "file_types"]:
                continue
            if key == "min_chunk_length":
                where["chunk_length"] = {"$gte": value}
            elif key == "max_chunk_length":
                where["chunk_length"] = {"$lte": value}
            elif isinstance(value, (str, int, float)):
                where[key] = {"$eq": value}
        
        return where if where else None

    def get_collection_info(self) -> Dict[str, Any]:
        """Optimize edilmiş collection bilgileri"""
        try:
            if not self.collection:
                return {"error": "collection is None"}
                
            count = self.collection.count()
            info = {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "chroma_path": self.chroma_path,
                "stats": self.get_stats(),
                "performance_optimized": True,
            }
            
            # Sadece gerekirse detailed info
            if count > 0 and count < 10000:  # Küçük collection'lar için
                sample_size = min(50, count)  # Daha az sample
                sample = self.collection.get(limit=sample_size, include=["metadatas"])
                if sample and sample.get("metadatas"):
                    sources = set()
                    file_types = set()
                    for metadata in sample["metadatas"] or []:
                        if metadata:
                            if "source_file" in metadata:
                                sources.add(metadata["source_file"])
                            if "file_type" in metadata:
                                file_types.add(metadata["file_type"])
                    info["sample_sources"] = list(sources)
                    info["sample_file_types"] = list(file_types)
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Collection info hatası: {e}")
            return {"error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Cache'li istatistikler"""
        with self._lock:
            if (self._stats_cache and self._stats_cache_time and 
                (datetime.now() - self._stats_cache_time).total_seconds() < self._cache_ttl):
                return self._stats_cache.copy()
        
        self._update_stats()
        return self.stats.copy()

    def clear_cache(self):
        """Cache temizle"""
        with self._lock:
            self._stats_cache = None
            self._stats_cache_time = None
            self._get_directory_size_cached.cache_clear()
        logger.info("✅ Cache temizlendi")

    def reset_collection(self):
        """Collection'ı sıfırla (yeni yapı için)"""
        try:
            if self.client and self.collection_name:
                try:
                    self.client.delete_collection(name=self.collection_name)
                    logger.info(f"✅ Collection '{self.collection_name}' silindi")
                except Exception as e:
                    logger.warning(f"Collection silme hatası: {e}")
                
                # Local embedding function tanımla
                from embedder import LocalEmbedder
                
                def embedding_function(texts):
                    embedder = LocalEmbedder(model=config.EMBEDDING_MODEL)
                    if isinstance(texts, str):
                        texts = [texts]
                    embeddings = []
                    for text in texts:
                        embedding = embedder.embed_single(text)
                        embeddings.append(embedding.tolist())
                    return embeddings
                
                # Custom embedding function class
                class LocalEmbeddingFunction:
                    def __call__(self, input):
                        return embedding_function(input)
                
                # Yeniden oluştur - Local embedding function ile
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=LocalEmbeddingFunction(),
                    metadata={
                        "hnsw:space": "cosine",
                        "description": "RAG documents collection with local embeddings"
                    },
                )
                logger.info(f"✅ Collection '{self.collection_name}' yeniden oluşturuldu")
                
        except Exception as e:
            logger.error(f"❌ Collection reset hatası: {e}")
            raise


def main():
    """Optimize edilmiş main function"""
    chroma_path = "./chroma"
    input_file = "uploads_with_embed.json"
    collection_name = "rag_documents"

    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("🚀 YENİ CHROMADB KONFİGÜRASYONU ile uploads_with_embed.json aktarılıyor...")

    if not os.path.exists(input_file):
        logger.error(f"❌ Giriş dosyası bulunamadı: {input_file}")
        return

    try:
        # Yeni konfigürasyon ile manager
        chroma_manager = ChromaDBManager(chroma_path, collection_name)

        logger.info(f"📄 JSON dosyası yükleniyor: {input_file}")
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            logger.warning(f"⚠️ JSON dosyası boş: {input_file}")
            return

        logger.info(f"📊 {len(data)} doküman bulundu")

        # Optimize edilmiş batch import
        result = chroma_manager.add_documents_batch(
            data=data, 
            batch_size=2000,        # Daha büyük batch
            skip_duplicates=False   # Hızlandırma için false
        )

        logger.info("📊 YENİ KONFİGÜRASYON IMPORT RAPORU:")
        logger.info(f"   İşlenen: {result['total_processed']:,}")
        logger.info(f"   Eklenen: {result['total_added']:,}")
        logger.info(f"   Başarı oranı: {result['success_rate']:.1%}")
        
        if result["errors"]:
            logger.warning(f"⚠️ {len(result['errors'])} hata oluştu")

        # Final istatistikler
        final_stats = chroma_manager.get_stats()
        logger.info("📊 FİNAL İSTATİSTİKLER:")
        logger.info(f"   Toplam chunk: {final_stats['total_chunks']:,}")
        logger.info(f"   Index boyutu: {final_stats['index_size_mb']:.2f} MB")

        logger.info("✅ YENİ KONFİGÜRASYON ile import tamamlandı!")

    except Exception as e:
        logger.error(f"❌ Ana işlem hatası: {e}")
        raise


if __name__ == "__main__":
    main()