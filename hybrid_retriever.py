import chromadb
import re
from typing import List, Dict, Any, Tuple, Optional, Union
from embedder import LocalEmbedder
from config import config
from query_processor import QueryProcessor


class HybridRetriever:
    """Semantic ve keyword-based aramayı birleştiren hibrit retrieval sistemi"""

    def __init__(self, chroma_path: str = "./chroma"):
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.model = LocalEmbedder(model=config.EMBEDDING_MODEL)
        self.query_processor = QueryProcessor()
        
        # Local embedding function tanımla
        def embedding_function(texts):
            if isinstance(texts, str):
                texts = [texts]
            embeddings = []
            for text in texts:
                embedding = self.model.embed_single(text)
                embeddings.append(embedding.tolist())
            return embeddings
        
        # Custom embedding function class
        class LocalEmbeddingFunction:
            def __call__(self, input):
                return embedding_function(input)
        
        # Collection'ı oluştur
        try:
            self.collection = self.client.get_collection("rag_documents")
        except:
            self.collection = self.client.create_collection(
                name="rag_documents",
                embedding_function=LocalEmbeddingFunction()
            )

        # TF-IDF için basit implementasyon
        self.keyword_weights = {
            "tarih": 2.0,
            "süre": 2.0,
            "değer": 2.0,
            "kural": 2.5,
            "prosedür": 2.0,
            "şart": 2.0,
        }

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.embed_single(text)
        return embedding.tolist()

    def semantic_search(
        self, query: str, n_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """Semantic similarity ile arama"""
        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS

        query_embedding = self.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, config.MAX_N_RESULTS),
            include=["documents", "metadatas", "distances"],
        )

        # ChromaDB QueryResult'ı Dict'e çevir
        return {
            "documents": results.get("documents", [[]]),
            "metadatas": results.get("metadatas", [[]]),
            "distances": results.get("distances", [[]]),
        }

    def keyword_search(
        self, query: str, n_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Keyword-based arama"""
        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS

        # Tüm dokümanları al (bu gerçek uygulamada optimize edilmeli)
        all_docs = self.collection.get(include=["documents", "metadatas"])

        processed_query = self.query_processor.process_query(query)
        keywords = processed_query["keywords"]

        scored_docs = []

        # None check'leri ekle
        documents = all_docs.get("documents", [])
        metadatas = all_docs.get("metadatas", [])
        ids = all_docs.get("ids", [])

        if not documents or not metadatas:
            return []

        for i, (doc, metadata) in enumerate(zip(documents, metadatas)):
            if doc and metadata:  # None check
                score = self.calculate_keyword_score(doc, keywords)
                if score > 0:
                    doc_id = ids[i] if i < len(ids) else f"doc_{i}"
                    scored_docs.append(
                        {
                            "document": doc,
                            "metadata": metadata,
                            "score": score,
                            "id": doc_id,
                        }
                    )

        # Score'a göre sırala
        scored_docs.sort(key=lambda x: x["score"], reverse=True)

        return scored_docs[:n_results]

    def calculate_keyword_score(self, document: str, keywords: List[str]) -> float:
        """Doküman için keyword score hesapla"""
        doc_lower = document.lower()
        score = 0.0

        for keyword in keywords:
            # Tam eşleşme
            if keyword in doc_lower:
                weight = self.keyword_weights.get(keyword, 1.0)
                # Kelime sıklığını da dikkate al
                count = len(re.findall(r"\b" + re.escape(keyword) + r"\b", doc_lower))
                score += count * weight

        # Doküman uzunluğuna göre normalize et
        doc_length = len(document.split())
        if doc_length > 0:
            score = score / (doc_length**0.5)  # SQRT normalization

        return score

    def hybrid_search(
        self,
        query: str,
        n_results: Optional[int] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Hibrit arama: semantic + keyword"""
        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS

        # Semantic arama
        semantic_results = self.semantic_search(query, n_results * 2)

        # Keyword arama
        keyword_results = self.keyword_search(query, n_results * 2)

        # Sonuçları birleştir ve skorla
        combined_results = {}

        # Semantic sonuçlar
        docs = semantic_results.get("documents", [[]])[0]
        metadatas = semantic_results.get("metadatas", [[]])[0]
        distances = semantic_results.get("distances", [[]])[0]

        for i, (doc, metadata, distance) in enumerate(zip(docs, metadatas, distances)):
            doc_id = f"semantic_{i}"
            semantic_score = 1.0 - distance  # Distance'i similarity'ye çevir

            combined_results[doc_id] = {
                "document": doc,
                "metadata": metadata,
                "semantic_score": semantic_score,
                "keyword_score": 0.0,
                "combined_score": semantic_score * semantic_weight,
                "source": "semantic",
            }

        # Keyword sonuçları ekle/güncelle
        for result in keyword_results:
            doc = result["document"]
            # Aynı dokümanı bul
            doc_id = None
            for existing_id, existing_result in combined_results.items():
                if existing_result["document"] == doc:
                    doc_id = existing_id
                    break

            if doc_id:
                # Mevcut sonucu güncelle
                combined_results[doc_id]["keyword_score"] = result["score"]
                combined_results[doc_id]["combined_score"] = (
                    combined_results[doc_id]["semantic_score"] * semantic_weight
                    + result["score"] * keyword_weight
                )
                combined_results[doc_id]["source"] = "hybrid"
            else:
                # Yeni sonuç ekle
                new_id = f"keyword_{len(combined_results)}"
                combined_results[new_id] = {
                    "document": doc,
                    "metadata": result["metadata"],
                    "semantic_score": 0.0,
                    "keyword_score": result["score"],
                    "combined_score": result["score"] * keyword_weight,
                    "source": "keyword",
                }

        # Combined score'a göre sırala
        sorted_results = sorted(
            combined_results.values(), key=lambda x: x["combined_score"], reverse=True
        )

        return sorted_results[:n_results]

    def advanced_retrieve(
        self, query: str, n_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """Gelişmiş retrieval pipeline"""
        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS

        # Query'yi işle
        processed_query = self.query_processor.process_query(query)

        # Farklı query varyantları dene
        all_results = []

        for variant in processed_query["expanded"][:3]:  # En fazla 3 varyant
            results = self.hybrid_search(variant, n_results)
            all_results.extend(results)

        # Sonuçları deduplicate et ve skorla
        unique_results = {}
        for result in all_results:
            doc_text = result["document"]
            if doc_text not in unique_results:
                unique_results[doc_text] = result
            else:
                # Daha yüksek score'u tut
                if (
                    result["combined_score"]
                    > unique_results[doc_text]["combined_score"]
                ):
                    unique_results[doc_text] = result

        # Final sıralama
        final_results = sorted(
            unique_results.values(), key=lambda x: x["combined_score"], reverse=True
        )[:n_results]

        return {
            "results": final_results,
            "query_analysis": processed_query,
            "total_found": len(final_results),
        }

    def filter_by_similarity_threshold(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Similarity threshold'una göre filtrele"""
        filtered = []
        for result in results:
            if result.get("combined_score", 0) >= config.SIMILARITY_THRESHOLD:
                filtered.append(result)
        return filtered