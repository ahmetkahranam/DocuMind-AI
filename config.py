    # RAG Chatbot Configuration
import os
from typing import Dict, Any
from env_loader import *


class RAGConfig:
    # Embedding Configuration - Local Models
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # Local sentence-transformers model
    EMBEDDING_DIMENSION = 384  # MiniLM dimension
    NORMALIZE_EMBEDDINGS = True

    # Retrieval Configuration
    DEFAULT_N_RESULTS = 10  # Increased from 5
    MAX_N_RESULTS = 20  # Increased from 10
    SIMILARITY_THRESHOLD = 0.01  # Much lower threshold - daha fazla chunk dahil et
    RERANK_TOP_K = 3

    # Text Processing Configuration
    MAX_CHUNK_SIZE = 1024  # Increased from 512 - daha büyük chunk'lar
    CHUNK_OVERLAP = 100  # Increased from 50 - daha fazla overlap
    MAX_CONTEXT_LENGTH = 16000  # Increased from 4000 - çok daha fazla context

    # LLM Configuration - Ollama Local Models
    LLM_MODEL = "deepseek-r1:latest"  # Local Ollama DeepSeek-R1 model
    LLM_TEMPERATURE = 0.1  # Lower for more factual responses
    LLM_MAX_TOKENS = 2048  # Increased from 512 for complete responses

    # Alternative Ollama models (örnek model isimleri)
    OLLAMA_LLM_MODELS = {
        "deepseek-r1": "deepseek-r1:latest",
        "llama2": "llama2:latest",
        "tinyllama": "tinyllama:latest",
    }

    # Quality Control
    MIN_ANSWER_LENGTH = 20
    MAX_ANSWER_LENGTH = 1000
    REQUIRE_SOURCE_VALIDATION = True

    # Prompt Templates
    SYSTEM_PROMPT = """Sen bir doküman analiz asistanısın. Verilen belgelerden kesin, doğru ve yararlı bilgiler çıkararak cevap vermelisin.

KURALLAR:
1. SADECE sorulan soruyu yanıtla - başka konuları dahil etme
2. Sadece verilen belgelerden bilgi kullan
3. Belirsiz olduğun konularda "Bu konuda kesin bilgi bulunamadı" de
4. Sayısal bilgileri (tarih, süre, puan) kesin olarak belirt
5. Alakasız bilgileri yanıta dahil etme
6. Tek bir konuya odaklan
7. Asla kaynak belge adı veya dosya uzantısı belirtme
8. Türkçe dilbilgisi kurallarına uy"""

    RAG_PROMPT_TEMPLATE = """
{system_prompt}

SORU: {question}

İLGİLİ BELGELER:
{context}

ÖNEMLİ: Sadece soruyla DOĞRUDAN alakalı bilgileri yanıtla. Başka konulardan bahsetme!

CEVAP (Kısa, net ve sadece soruyla alakalı):
"""

    FALLBACK_RESPONSE = "Bu konuda belgelerimde yeterli bilgi bulunmuyor. Lütfen daha spesifik bir soru sorun veya farklı bir konuda soru sormayı deneyin."


# Global config instance
config = RAGConfig()