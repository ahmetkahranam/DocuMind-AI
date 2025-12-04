import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer

# File reading utility with encoding safety
def safe_read_file(file_path):
    """Safely read file content with proper encoding detection"""
    try:
        filename = os.path.basename(file_path)
        file_extension = os.path.splitext(filename)[1].lower()
        
        print(f"[+] Reading file: {filename} (extension: {file_extension})")
        
        # Handle PDF files
        if file_extension == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                print(f"[+] PDF extracted: {len(text)} characters")
                return text
            except ImportError:
                print("[!] PyPDF2 not installed, treating as text")
            except Exception as e:
                print(f"[!] PDF extraction failed: {e}")
        
        # Handle Word documents
        elif file_extension in ['.doc', '.docx']:
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                print(f"[+] Word document extracted: {len(text)} characters")
                return text
            except ImportError:
                print("[!] python-docx not installed, treating as text")
            except Exception as e:
                print(f"[!] Word extraction failed: {e}")
        
        # Handle text files with encoding detection
        content = None
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                print(f"[+] File read successfully with {encoding} encoding")
                break
            except UnicodeDecodeError as e:
                print(f"[!] Failed with {encoding}: {e}")
                continue
            except Exception as e:
                print(f"[!] Error with {encoding}: {e}")
                continue
        
        # If all encodings failed, try binary with error handling
        if content is None:
            try:
                with open(file_path, 'rb') as file:
                    binary_data = file.read()
                content = binary_data.decode('utf-8', errors='replace')
                print(f"[+] Binary read with error replacement: {len(content)} characters")
            except Exception as e:
                print(f"[!] Binary read failed: {e}")
                return None
        
        return content
        
    except Exception as e:
        print(f"[!] Critical error reading {file_path}: {e}")
        return None

import json
import logging
import time
import hashlib
from typing import List, Dict, Any, Optional, Union
import numpy as np
from pathlib import Path
import pickle
from datetime import datetime, timedelta
import threading
from multiprocessing import cpu_count

import requests
from tqdm import tqdm
from config import config

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Embedding cache sistemi"""

    def __init__(self, cache_dir: str = "./embedding_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_file = os.path.join(cache_dir, "embedding_cache.pkl")
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, np.ndarray]:
        """Cache'i yükle"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Cache yüklenemedi: {e}")
        return {}

    def _save_cache(self):
        """Cache'i kaydet"""
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Cache kaydedilemedi: {e}")

    def get_hash(self, text: str, model_name: str) -> str:
        """Text + model için hash oluştur"""
        combined = f"{model_name}:{text}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """Cache'den embedding al"""
        hash_key = self.get_hash(text, model_name)
        return self.cache.get(hash_key)

    def set(self, text: str, model_name: str, embedding: np.ndarray):
        """Cache'e embedding ekle"""
        hash_key = self.get_hash(text, model_name)
        self.cache[hash_key] = embedding

        # Periyodik kaydetme (her 100 yeni embedding'de)
        if len(self.cache) % 100 == 0:
            self._save_cache()

    def clear(self):
        """Cache'i temizle"""
        self.cache.clear()
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def get_stats(self) -> Dict[str, Any]:
        """Cache istatistikleri"""
        return {
            "total_embeddings": len(self.cache),
            "cache_size_mb": (
                os.path.getsize(self.cache_file) / (1024 * 1024)
                if os.path.exists(self.cache_file)
                else 0
            ),
        }


class LocalEmbedder:
    """Local SentenceTransformer embedding sistemi"""

    # Desteklenen local modeller
    SUPPORTED_MODELS = {
        "paraphrase-multilingual-MiniLM-L12-v2": {"dimensions": 384, "max_tokens": 128},
        "paraphrase-multilingual-mpnet-base-v2": {"dimensions": 768, "max_tokens": 128},
        "all-MiniLM-L6-v2": {"dimensions": 384, "max_tokens": 256},
        "all-mpnet-base-v2": {"dimensions": 768, "max_tokens": 384},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        enable_cache: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        custom_dimensions: Optional[int] = None,
    ):
        self.model = model
        self.enable_cache = enable_cache
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.custom_dimensions = custom_dimensions
        
        # SentenceTransformer modelini yükle
        print(f"🤖 SentenceTransformer modeli yükleniyor: {self.model}")
        self.client = SentenceTransformer(self.model)
        
        # Cache'i başlat
        self.cache = EmbeddingCache() if enable_cache else None
        
        # Model bilgilerini al
        self.model_info = self.SUPPORTED_MODELS.get(model, {
            "dimensions": custom_dimensions or 384,
            "max_tokens": 128
        })
        
        logger.info(f"🤖 Local Embedder başlatıldı")
        print(f"   Model: {self.model}")
        logger.info(f"   Dimensions: {self.model_info['dimensions']}")
        logger.info(f"   Max tokens: {self.model_info['max_tokens']}")
        logger.info(f"   Cache: {'Aktif' if self.cache else 'Devre dışı'}")

    def _validate_text(self, text: str) -> str:
        """Metni valide et ve temizle"""
        if not text:
            return ""
        
        # String'e çevir
        text = str(text).strip()
        
        # Boş string kontrolü
        if not text:
            return ""
        
        # Çok uzun metinleri kırp (model token limiti)
        if len(text) > 8000:  # Conservative limit
            logger.warning(f"Metin çok uzun, kırpılıyor: {len(text)} -> 8000 karakter")
            text = text[:8000]
        
        return text

    def _call_embedding_api(self, texts: List[str], attempt: int = 1) -> List[np.ndarray]:
        """Local SentenceTransformer ile embedding üret"""
        try:
            # Metinleri valide et
            validated_texts = []
            for text in texts:
                validated_text = self._validate_text(text)
                validated_texts.append(validated_text)
            
            # Boş metinleri filtrele
            non_empty_texts = [t for t in validated_texts if t]
            if not non_empty_texts:
                logger.warning("Tüm metinler boş, sıfır vektörler döndürülüyor")
                dimension = self.model_info["dimensions"]
                return [np.zeros(dimension, dtype=np.float32) for _ in texts]
            
            # SentenceTransformer ile embedding üret
            api_embeddings = self.client.encode(
                non_empty_texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=False
            )
            
            # Sonuçları liste olarak dönüştür
            if len(api_embeddings.shape) == 1:
                api_embeddings = [api_embeddings]
            else:
                api_embeddings = [emb for emb in api_embeddings]
            
            # Boş metinler için sıfır vektör ekle
            final_embeddings = []
            api_idx = 0
            
            for original_text in validated_texts:
                if original_text:  # Boş değilse model sonucunu kullan
                    if api_idx < len(api_embeddings):
                        final_embeddings.append(api_embeddings[api_idx].astype(np.float32))
                        api_idx += 1
                    else:
                        # Fallback
                        dimension = self.model_info["dimensions"]
                        final_embeddings.append(np.zeros(dimension, dtype=np.float32))
                else:  # Boş ise sıfır vektör
                    dimension = self.model_info["dimensions"]
                    final_embeddings.append(np.zeros(dimension, dtype=np.float32))
            
            return final_embeddings
            
        except Exception as e:
            logger.error(f"Embedding hatası (deneme {attempt}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.info(f"⏳ {delay:.1f}s beklenip tekrar denenecek...")
                time.sleep(delay)
                return self._call_embedding_api(texts, attempt + 1)
            else:
                # Son deneme başarısız - sıfır vektör döndür
                logger.error("Embedding üretimi başarısız, sıfır vektörler döndürülüyor")
                dimension = self.model_info["dimensions"]
                return [np.zeros(dimension, dtype=np.float32) for _ in texts]

    def embed_single(self, text: str, normalize: bool = False) -> np.ndarray:
        """Tek metin için embedding"""
        validated_text = self._validate_text(text)
        
        if not validated_text:
            logger.warning("Boş metin için sıfır vektör döndürülüyor")
            return np.zeros(self.model_info["dimensions"], dtype=np.float32)
        
        # Cache kontrolü
        if self.cache:
            cached_embedding = self.cache.get(validated_text, self.model)
            if cached_embedding is not None:
                logger.debug("Cache'den embedding alındı")
                return cached_embedding
        
        # API çağrısı
        embeddings = self._call_embedding_api([validated_text])
        embedding = embeddings[0]
        
        # Normalize (gerekirse)
        if normalize:
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
        
        # Cache'e kaydet
        if self.cache:
            self.cache.set(validated_text, self.model, embedding)
        
        return embedding

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 50,  # Local için batch size
        normalize: bool = False,
        show_progress: bool = True,
    ) -> List[np.ndarray]:
        """Batch embedding işlemi"""
        if not texts:
            logger.warning("Boş metin listesi")
            return []

        logger.info(f"📊 {len(texts)} metin için embedding hesaplanıyor...")
        logger.info(f"Model: {self.model}, Batch size: {batch_size}")

        # Metinleri valide et
        validated_texts = []
        for i, text in enumerate(texts):
            validated_text = self._validate_text(text)
            validated_texts.append(validated_text)
            if not validated_text:
                logger.warning(f"Boş metin tespit edildi (index: {i})")

        # Cache kontrolü
        embeddings = []
        cached_results = {}
        texts_to_process = []
        text_indices = []

        if self.cache:
            cache_hits = 0
            for i, text in enumerate(validated_texts):
                if not text:
                    cached_results[i] = np.zeros(self.model_info["dimensions"], dtype=np.float32)
                else:
                    cached = self.cache.get(text, self.model)
                    if cached is not None:
                        cached_results[i] = cached
                        cache_hits += 1
                    else:
                        texts_to_process.append(text)
                        text_indices.append(i)
            
            logger.info(f"💾 Cache hits: {cache_hits}/{len(validated_texts)}")
        else:
            texts_to_process = []
            text_indices = []
            for i, text in enumerate(validated_texts):
                if not text:
                    cached_results[i] = np.zeros(self.model_info["dimensions"], dtype=np.float32)
                else:
                    texts_to_process.append(text)
                    text_indices.append(i)

        # API çağrıları
        if texts_to_process:
            logger.info(f"🔄 API ile işlenecek metin sayısı: {len(texts_to_process)}")
            progress_bar = tqdm(total=len(texts_to_process), desc="Embedding", disable=not show_progress)
            
            for i in range(0, len(texts_to_process), batch_size):
                batch = texts_to_process[i:i + batch_size]
                logger.debug(f"Batch işleniyor: {i//batch_size + 1}/{(len(texts_to_process)-1)//batch_size + 1}")
                
                batch_embeddings = self._call_embedding_api(batch)
                
                # Sonuçları kaydet
                for j, embedding in enumerate(batch_embeddings):
                    if i + j < len(text_indices):
                        text_idx = text_indices[i + j]
                        text = texts_to_process[i + j]
                        
                        # Embedding kontrolü
                        if embedding is None or np.isnan(embedding).any():
                            logger.warning(f"Geçersiz embedding tespit edildi (index: {text_idx})")
                            embedding = np.zeros(self.model_info["dimensions"], dtype=np.float32)
                        
                        # Normalize (gerekirse)
                        if normalize:
                            norm = np.linalg.norm(embedding)
                            if norm > 0:
                                embedding = embedding / norm
                        
                        # Cache'e kaydet
                        if self.cache and text:
                            self.cache.set(text, self.model, embedding)
                        
                        cached_results[text_idx] = embedding
                
                progress_bar.update(len(batch))
                
                # Rate limiting (Local processing)
                time.sleep(0.1)
            
            progress_bar.close()

        # Sonuçları sırala
        final_embeddings = []
        for i in range(len(texts)):
            if i in cached_results:
                final_embeddings.append(cached_results[i])
            else:
                logger.warning(f"Embedding eksik (index: {i}), sıfır vektör ekleniyor")
                final_embeddings.append(np.zeros(self.model_info["dimensions"], dtype=np.float32))

        logger.info(f"✅ {len(final_embeddings)} embedding hazırlandı")
        return final_embeddings

    def embed_with_ensemble(
        self,
        texts: List[str],
        models: Optional[List[str]] = None,
        weights: Optional[List[float]] = None,
    ) -> List[np.ndarray]:
        """Ensemble embedding (çoklu model birleştirme)"""
        models = models or ["text-embedding-3-small", "text-embedding-ada-002"]
        weights = weights or [1.0] * len(models)

        if len(models) != len(weights):
            raise ValueError("Model sayısı ve ağırlık sayısı eşit olmalı")

        logger.info(f"🔗 Ensemble embedding: {len(models)} model")

        all_embeddings = []
        original_model = self.model

        # Her model için embedding hesapla
        for model_name, weight in zip(models, weights):
            logger.info(f"📊 Model işleniyor: {model_name} (ağırlık: {weight})")
            
            # Geçici olarak modeli değiştir
            self.model = model_name
            self.model_info = self.SUPPORTED_MODELS.get(model_name, {
                "dimensions": 1536,
                "max_tokens": 8192
            })
            
            model_embeddings = self.embed_batch(texts, show_progress=False)
            all_embeddings.append((model_embeddings, weight))

        # Orijinal modeli geri yükle
        self.model = original_model
        self.model_info = self.SUPPORTED_MODELS.get(original_model, {
            "dimensions": 1536,
            "max_tokens": 8192
        })

        # Ağırlıklı ortalama
        logger.info("🔄 Ensemble birleştirme yapılıyor...")
        ensemble_embeddings = []

        for i in range(len(texts)):
            combined_embedding = None
            total_weight = 0

            for model_embeddings, weight in all_embeddings:
                if i < len(model_embeddings) and model_embeddings[i] is not None:
                    if combined_embedding is None:
                        combined_embedding = model_embeddings[i] * weight
                    else:
                        # Boyut uyumsuzluğu kontrolü
                        if len(combined_embedding) != len(model_embeddings[i]):
                            logger.warning(f"Boyut uyumsuzluğu: {len(combined_embedding)} vs {len(model_embeddings[i])}")
                            continue
                        combined_embedding += model_embeddings[i] * weight
                    total_weight += weight

            if combined_embedding is not None and total_weight > 0:
                combined_embedding /= total_weight
                # Normalize
                norm = np.linalg.norm(combined_embedding)
                if norm > 0:
                    combined_embedding /= norm
                ensemble_embeddings.append(combined_embedding)
            else:
                # Fallback: sıfır vektör
                ensemble_embeddings.append(np.zeros(self.model_info["dimensions"], dtype=np.float32))

        logger.info("✅ Ensemble embedding tamamlandı")
        return ensemble_embeddings

    def benchmark_models(
        self, test_texts: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """Model performance benchmark"""
        test_texts = test_texts or [
            "Bu bir test cümlesidir.",
            "Merhaba dünya! Nasılsın?",
            "Eduroam ağına nasıl bağlanabilirim?",
        ]

        logger.info("🏃 Model benchmark başlıyor...")
        
        results = {}
        original_model = self.model

        for model_name in self.SUPPORTED_MODELS.keys():
            logger.info(f"⏱️ Test ediliyor: {model_name}")

            try:
                # Geçici olarak modeli değiştir
                self.model = model_name
                self.model_info = self.SUPPORTED_MODELS[model_name]
                
                start_time = time.time()

                # Test embedding
                embeddings = self.embed_batch(test_texts, show_progress=False)

                end_time = time.time()
                duration = end_time - start_time

                # Embedding kalitesi (basit metrik)
                valid_embeddings = [emb for emb in embeddings if emb is not None]
                if valid_embeddings:
                    avg_norm = np.mean([np.linalg.norm(emb) for emb in valid_embeddings])
                else:
                    avg_norm = 0.0

                results[model_name] = {
                    "duration_seconds": duration,
                    "texts_per_second": len(test_texts) / duration if duration > 0 else 0,
                    "avg_embedding_norm": float(avg_norm),
                    "embedding_dimension": self.model_info["dimensions"],
                    "max_tokens": self.model_info["max_tokens"],
                    "valid_embeddings": len(valid_embeddings),
                }

                logger.info(f"   ⚡ {len(test_texts)/duration:.1f} text/sec, dim: {self.model_info['dimensions']}")

            except Exception as e:
                logger.error(f"   ❌ Benchmark hatası {model_name}: {e}")
                results[model_name] = {"error": str(e)}

        # Orijinal modeli geri yükle
        self.model = original_model
        self.model_info = self.SUPPORTED_MODELS.get(original_model, {
            "dimensions": 1536,
            "max_tokens": 8192
        })

        return results

    def get_model_info(self) -> Dict[str, Any]:
        """Model bilgileri"""
        info = {
            "model": self.model,
            "dimensions": self.model_info["dimensions"],
            "max_tokens": self.model_info["max_tokens"],
            "custom_dimensions": self.custom_dimensions,
            "cache_enabled": self.cache is not None,
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
        }

        if self.cache:
            info["cache_stats"] = self.cache.get_stats()

        return info

    def cleanup(self):
        """Cleanup işlemleri"""
        if self.cache:
            self.cache._save_cache()
        logger.info("🧹 Cleanup tamamlandı")


def validate_input_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Input verisini valide et"""
    stats = {
        "total_documents": len(data),
        "documents_with_chunks": 0,
        "total_chunks": 0,
        "empty_chunks": 0,
        "valid_chunks": 0,
        "issues": []
    }
    
    for doc_idx, item in enumerate(data):
        if not isinstance(item, dict):
            stats["issues"].append(f"Doküman {doc_idx}: Dict değil")
            continue
            
        chunks = item.get("chunks", [])
        if not chunks:
            stats["issues"].append(f"Doküman {doc_idx}: Chunk'lar boş")
            continue
            
        if not isinstance(chunks, list):
            stats["issues"].append(f"Doküman {doc_idx}: Chunks liste değil")
            continue
            
        stats["documents_with_chunks"] += 1
        stats["total_chunks"] += len(chunks)
        
        # Chunk'ları kontrol et
        for chunk_idx, chunk in enumerate(chunks):
            if not chunk or not str(chunk).strip():
                stats["empty_chunks"] += 1
                stats["issues"].append(f"Doküman {doc_idx}, Chunk {chunk_idx}: Boş")
            else:
                stats["valid_chunks"] += 1
    
    return stats


def process_documents_with_embeddings(
    input_file: str, output_file: str, model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Dokümanları embedding'lerle işle"""
    print("🚀 Embedding işlemi başlıyor...")
    # Default config
    default_config = {
        "model": "paraphrase-multilingual-MiniLM-L12-v2",
        "custom_dimensions": None,
        "use_ensemble": False,
        "ensemble_models": None,
        "batch_size": 50,
        "use_cache": True,
        "max_retries": 3,
        "retry_delay": 1.0,
        "validate_input": True,
    }

    if model_config:
        default_config.update(model_config)

    print("🚀 Embedding işlemi başlıyor...")
    print(f"📄 Girdi: {input_file}")
    print(f"💾 Çıktı: {output_file}")

    # Input dosyasını yükle
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Input dosyası okunamadı: {e}")
        raise

    if not data:
        logger.error("❌ Input dosyası boş")
        return {"error": "Empty input file"}

    # Input verisini valide et
    if default_config["validate_input"]:
        logger.info("🔍 Input verisi valide ediliyor...")
        validation_stats = validate_input_data(data)
        
        logger.info("📊 VERİ VALİDASYON SONUÇLARI:")
        logger.info(f"   Toplam doküman: {validation_stats['total_documents']}")
        logger.info(f"   Chunk'lı doküman: {validation_stats['documents_with_chunks']}")
        logger.info(f"   Toplam chunk: {validation_stats['total_chunks']}")
        logger.info(f"   Geçerli chunk: {validation_stats['valid_chunks']}")
        logger.info(f"   Boş chunk: {validation_stats['empty_chunks']}")
        
        if validation_stats["issues"]:
            logger.warning(f"⚠️ {len(validation_stats['issues'])} sorun tespit edildi")
            for issue in validation_stats["issues"][:10]:  # İlk 10 sorunu göster
                logger.warning(f"   - {issue}")
            if len(validation_stats["issues"]) > 10:
                logger.warning(f"   ... ve {len(validation_stats['issues']) - 10} sorun daha")

    # Embedder oluştur
    embedder = LocalEmbedder(
        model=default_config["model"],
        enable_cache=default_config["use_cache"],
        max_retries=default_config["max_retries"],
        retry_delay=default_config["retry_delay"],
        custom_dimensions=default_config["custom_dimensions"],
    )

    # İstatistikler
    total_documents = len(data)
    total_chunks = sum(len(item.get("chunks", [])) for item in data)
    processed_chunks = 0
    successful_documents = 0

    print(f"📊 {total_documents} doküman, {total_chunks} chunk işlenecek")

    try:
        for doc_idx, item in enumerate(data, 1):
            chunks = item.get("chunks", [])
            if not chunks:
                logger.warning(f"⚠️ Doküman {doc_idx} chunk'ları boş, atlanıyor")
                item["embeddings"] = []
                continue

            filename = item.get("filename", f"Document_{doc_idx}")
            logger.info(f"[{doc_idx}/{total_documents}] İşleniyor: {filename}")

            try:
                # Embedding hesapla
                if default_config["use_ensemble"] and default_config["ensemble_models"]:
                    embeddings = embedder.embed_with_ensemble(
                        chunks, models=default_config["ensemble_models"]
                    )
                else:
                    embeddings = embedder.embed_batch(
                        chunks, 
                        batch_size=default_config["batch_size"], 
                        show_progress=False
                    )

                # Numpy array'leri liste'ye çevir
                embeddings_list = []
                for emb in embeddings:
                    if emb is not None:
                        embeddings_list.append(emb.tolist())
                    else:
                        # Fallback: sıfır vektör
                        embeddings_list.append([0.0] * embedder.model_info["dimensions"])

                item["embeddings"] = embeddings_list
                processed_chunks += len(chunks)
                successful_documents += 1

                print(f"   ✅ {len(chunks)} chunk embedding tamamlandı")

            except Exception as e:
                logger.error(f"   ❌ Doküman {doc_idx} embedding hatası: {e}")
                # Fallback: boş embedding listesi
                item["embeddings"] = [[0.0] * embedder.model_info["dimensions"]] * len(chunks)

        # Sonuçları kaydet
        logger.info("💾 Sonuçlar kaydediliyor...")

        # Backup eski dosya
        if os.path.exists(output_file):
            backup_file = f"{output_file}.backup_{int(time.time())}"
            os.rename(output_file, backup_file)
            logger.info(f"📁 Backup oluşturuldu: {backup_file}")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Dosya boyutu kontrolü
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"✅ Embedding dosyası kaydedildi: {output_file} ({file_size:.2f} MB)")

        # Final istatistikler
        stats = {
            "total_documents": total_documents,
            "successful_documents": successful_documents,
            "total_chunks": total_chunks,
            "processed_chunks": processed_chunks,
            "output_file_size_mb": file_size,
            "model_info": embedder.get_model_info(),
            "success_rate": (successful_documents / total_documents) * 100 if total_documents > 0 else 0,
        }

        print("📊 EMBEDDING İSTATİSTİKLERİ:")
        print(f"   İşlenen doküman: {successful_documents}/{total_documents}")
        print(f"   İşlenen chunk: {processed_chunks}")
        print(f"   Dosya boyutu: {file_size:.2f} MB")
        print(f"   Model: {default_config['model']}")
        print(f"   Başarı oranı: {stats['success_rate']:.1f}%")

        # Cleanup
        embedder.cleanup()

        return stats

    except Exception as e:
        logger.error(f"❌ Embedding işlemi hatası: {e}")
        embedder.cleanup()
        raise


def main():
    """uploads_base.json'daki verileri embed ederek uploads_with_embed.json'a kaydeder"""
    input_file = "uploads_base.json"
    output_file = "uploads_with_embed.json"

    embedding_config = {
        "model": "text-embedding-3-small",  # Veya "text-embedding-3-large"
        "custom_dimensions": None,  # Varsayılan boyut kullan
        "use_ensemble": False,
        "ensemble_models": ["paraphrase-multilingual-MiniLM-L12-v2"],
        "batch_size": 50,
        "use_cache": True,
        "max_retries": 3,
        "retry_delay": 1.0,
        "validate_input": True,
    }

    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        logger.info("🚀 uploads_base.json embedding işlemi başlıyor...")
        stats = process_documents_with_embeddings(
            input_file=input_file,
            output_file=output_file,
            model_config=embedding_config,
        )
        logger.info(f"✅ uploads_with_embed.json kaydedildi. İstatistikler: {stats}")
    except Exception as e:
        logger.error(f"❌ Ana işlem hatası: {e}")
        raise


# Ek yardımcı fonksiyonlar
def debug_input_file(input_file: str) -> Dict[str, Any]:
    """Input dosyasını detaylı şekilde debug et"""
    logger.info(f"🔍 Debug ediliyor: {input_file}")
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"❌ Dosya okunamadı: {e}")
        return {"error": str(e)}
    
    debug_info = {
        "file_exists": os.path.exists(input_file),
        "file_size_mb": os.path.getsize(input_file) / (1024 * 1024),
        "data_type": type(data).__name__,
        "data_length": len(data) if hasattr(data, '__len__') else "N/A",
    }
    
    if isinstance(data, list):
        debug_info["sample_documents"] = []
        for i, item in enumerate(data[:3]):  # İlk 3 dokümanı incele
            doc_info = {
                "index": i,
                "type": type(item).__name__,
                "keys": list(item.keys()) if isinstance(item, dict) else "N/A",
            }
            
            if isinstance(item, dict):
                chunks = item.get("chunks", [])
                doc_info["chunks_count"] = len(chunks)
                doc_info["chunks_type"] = type(chunks).__name__
                
                if chunks:
                    doc_info["sample_chunks"] = []
                    for j, chunk in enumerate(chunks[:2]):  # İlk 2 chunk'ı incele
                        chunk_info = {
                            "index": j,
                            "type": type(chunk).__name__,
                            "length": len(str(chunk)) if chunk else 0,
                            "preview": str(chunk)[:100] if chunk else "EMPTY",
                        }
                        doc_info["sample_chunks"].append(chunk_info)
            
            debug_info["sample_documents"].append(doc_info)
    
    logger.info("📊 DEBUG SONUÇLARI:")
    logger.info(f"   Dosya boyutu: {debug_info['file_size_mb']:.2f} MB")
    logger.info(f"   Veri tipi: {debug_info['data_type']}")
    logger.info(f"   Veri uzunluğu: {debug_info['data_length']}")
    
    return debug_info


def repair_input_file(input_file: str, output_file: str) -> Dict[str, Any]:
    """Bozuk input dosyasını onar"""
    logger.info(f"🔧 Onarılıyor: {input_file} -> {output_file}")
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"❌ Dosya okunamadı: {e}")
        return {"error": str(e)}
    
    if not isinstance(data, list):
        logger.error("❌ Veri liste formatında değil")
        return {"error": "Data is not a list"}
    
    repaired_data = []
    repair_stats = {
        "original_documents": len(data),
        "repaired_documents": 0,
        "removed_documents": 0,
        "fixed_chunks": 0,
        "removed_chunks": 0,
    }
    
    for doc_idx, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning(f"⚠️ Doküman {doc_idx}: Dict değil, atlanıyor")
            repair_stats["removed_documents"] += 1
            continue
        
        # Chunks kontrolü
        chunks = item.get("chunks", [])
        if not isinstance(chunks, list):
            logger.warning(f"⚠️ Doküman {doc_idx}: Chunks liste değil, düzeltiliyor")
            chunks = []
        
        # Chunk'ları temizle
        cleaned_chunks = []
        for chunk_idx, chunk in enumerate(chunks):
            if chunk and str(chunk).strip():
                cleaned_chunks.append(str(chunk).strip())
                repair_stats["fixed_chunks"] += 1
            else:
                repair_stats["removed_chunks"] += 1
        
        # Temizlenmiş chunks'ı kaydet
        item["chunks"] = cleaned_chunks
        
        # Dokümanı kaydet (boş chunks olsa bile)
        repaired_data.append(item)
        repair_stats["repaired_documents"] += 1
    
    # Onarılmış dosyayı kaydet
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(repaired_data, f, ensure_ascii=False, indent=2)
    
    logger.info("🔧 ONARIM SONUÇLARI:")
    logger.info(f"   Orijinal doküman: {repair_stats['original_documents']}")
    logger.info(f"   Onarılan doküman: {repair_stats['repaired_documents']}")
    logger.info(f"   Kaldırılan doküman: {repair_stats['removed_documents']}")
    logger.info(f"   Düzeltilen chunk: {repair_stats['fixed_chunks']}")
    logger.info(f"   Kaldırılan chunk: {repair_stats['removed_chunks']}")
    
    return repair_stats


def test_embedding_system():
    """Embedding sistemini test et"""
    logger.info("🧪 Embedding sistemi test ediliyor...")
    
    # Test verileri
    test_data = [
        {
            "filename": "test_doc_1.txt",
            "chunks": [
                "Bu bir test cümlesidir.",
                "İkinci test cümlesi.",
                "",  # Boş chunk
                "Üçüncü test cümlesi.",
            ]
        },
        {
            "filename": "test_doc_2.txt",
            "chunks": []  # Boş chunks
        },
        {
            "filename": "test_doc_3.txt",
            "chunks": [
                "Dördüncü test cümlesi.",
                "Beşinci test cümlesi.",
            ]
        }
    ]
    
    # Test dosyalarını oluştur
    test_input = "test_input.json"
    test_output = "test_output.json"
    
    with open(test_input, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # Test config
    test_config = {
        "model": "text-embedding-3-small",
        "batch_size": 10,
        "use_cache": True,
        "max_retries": 2,
        "validate_input": True,
    }
    
    try:
        # Test çalıştır
        stats = process_documents_with_embeddings(
            input_file=test_input,
            output_file=test_output,
            model_config=test_config,
        )
        
        logger.info("✅ Test başarılı!")
        logger.info(f"Test sonuçları: {stats}")
        
        # Temizlik
        if os.path.exists(test_input):
            os.remove(test_input)
        if os.path.exists(test_output):
            os.remove(test_output)
            
        return stats
        
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
        # Temizlik
        if os.path.exists(test_input):
            os.remove(test_input)
        if os.path.exists(test_output):
            os.remove(test_output)
        raise


if __name__ == "__main__":
    # Ana fonksiyon veya debug/test fonksiyonları çalıştır
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "debug":
            input_file = sys.argv[2] if len(sys.argv) > 2 else "uploads_base.json"
            debug_input_file(input_file)
            
        elif command == "repair":
            input_file = sys.argv[2] if len(sys.argv) > 2 else "uploads_base.json"
            output_file = sys.argv[3] if len(sys.argv) > 3 else "uploads_base_repaired.json"
            repair_input_file(input_file, output_file)
            
        elif command == "test":
            test_embedding_system()
            
        else:
            logger.error(f"Bilinmeyen komut: {command}")
            logger.info("Kullanım: python script.py [debug|repair|test] [input_file] [output_file]")
    else:
        # Normal çalıştırma
        main()