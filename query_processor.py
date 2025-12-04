import re
import string
from typing import List, Dict, Any, Tuple
from config import config


class QueryProcessor:
    """Kullanıcı sorgularını optimize eden ve genişleten sınıf"""

    def __init__(self):
        self.synonyms = {
            "belge": ["document", "doküman", "evrak"],
            "işlem": ["process", "prosedür", "adım"],
            "kural": ["rule", "yönetmelik", "şart"],
            "not": ["puan", "derece", "grade", "değerlendirme"],
            "ders": ["course", "lesson", "subject", "derslik"],
            "kullanıcı": ["user", "kişi", "başvurucu"],
            "hoca": ["öğretim görevlisi", "professor", "instructor", "teacher"],
            "kayıt": ["registration", "enrollment", "kaydolma"],
            "mezuniyet": ["graduation", "bitirme", "diploma"],
            "devamsızlık": ["absence", "yoklama", "attendance"],
            "geçme": ["passing", "başarı", "success"],
            "kalma": ["failure", "başarısızlık", "tekrar"],
        }

        self.question_patterns = {
            "nasıl": ["how", "procedure", "steps", "process"],
            "ne zaman": ["when", "date", "time", "schedule"],
            "nerede": ["where", "location", "place"],
            "kaç": ["how many", "count", "number", "amount"],
            "ne": ["what", "definition", "explanation"],
            "neden": ["why", "reason", "because"],
            "kim": ["who", "person", "responsible"],
        }

    def clean_query(self, query: str) -> str:
        """Sorguyu temizle ve normalize et"""
        # Küçük harfe çevir
        query = query.lower().strip()

        # Noktalama işaretlerini temizle (Türkçe karakterleri koru)
        query = re.sub(r"[^\w\s\çğıöşüÇĞIİÖŞÜ]", " ", query)

        # Çoklu boşlukları tek boşluk yap
        query = re.sub(r"\s+", " ", query)

        # Gereksiz kelimeleri çıkar
        stop_words = {
            "bir",
            "bu",
            "şu",
            "o",
            "ve",
            "ile",
            "için",
            "olan",
            "olur",
            "var",
            "yok",
        }
        words = [word for word in query.split() if word not in stop_words]

        return " ".join(words)

    def expand_query(self, query: str) -> List[str]:
        """Sorguyu sinonimlerle genişlet (her sinonim için varyant üret)"""
        expanded_queries = set([query])
        words = query.split()
        for i, word in enumerate(words):
            for key, synonyms in self.synonyms.items():
                if word == key or word in synonyms:
                    for synonym in [key] + synonyms:
                        if synonym != word:
                            new_words = words.copy()
                            new_words[i] = synonym
                            expanded_queries.add(" ".join(new_words))
        return list(expanded_queries)

    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Sorgudaki önemli varlıkları çıkar"""
        entities = {
            "numbers": re.findall(r"\d+", query),
            "dates": re.findall(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", query),
            "keywords": [],
        }

        # Anahtar kelimeler
        academic_keywords = [
            "sınav",
            "not",
            "ders",
            "kredi",
            "gpa",
            "ortalama",
            "mezuniyet",
            "kayıt",
            "harç",
            "burs",
            "devamsızlık",
            "disiplin",
            "yönetmelik",
        ]

        for keyword in academic_keywords:
            if keyword in query.lower():
                entities["keywords"].append(keyword)

        return entities

    def categorize_query(self, query: str) -> str:
        """Sorgu tipini kategorize et"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["nasıl", "how", "adım"]):
            return "procedure"
        elif any(word in query_lower for word in ["ne zaman", "when", "tarih"]):
            return "temporal"
        elif any(word in query_lower for word in ["nerede", "where", "yer"]):
            return "location"
        elif any(word in query_lower for word in ["kaç", "how many", "sayı"]):
            return "quantitative"
        elif any(word in query_lower for word in ["ne", "what", "nedir"]):
            return "definition"
        elif any(word in query_lower for word in ["neden", "why", "sebep"]):
            return "explanation"
        else:
            return "general"

    def process_query(self, query: str) -> Dict[str, Any]:
        """Sorguyu tam olarak işle ve analiz et"""
        processed = {
            "original": query,
            "cleaned": self.clean_query(query),
            "expanded": self.expand_query(query),
            "entities": self.extract_entities(query),
            "category": self.categorize_query(query),
            "keywords": self.extract_keywords(query),
        }

        return processed

    def extract_keywords(self, query: str) -> List[str]:
        """Sorgudaki anahtar kelimeleri çıkar"""
        # Basit keyword extraction
        words = self.clean_query(query).split()

        # En az 3 harfli kelimeleri al
        keywords = [word for word in words if len(word) >= 3]

        return keywords[:5]  # En fazla 5 keyword

    def generate_search_variants(self, query: str) -> List[str]:
        """Farklı arama varyantları oluştur"""
        processed = self.process_query(query)
        variants = [processed["cleaned"]]

        # Orijinal sorgu
        variants.append(query.strip())

        # Genişletilmiş sorgular
        variants.extend(processed["expanded"][:3])

        # Sadece anahtar kelimeler
        if processed["keywords"]:
            variants.append(" ".join(processed["keywords"]))

        return list(set(variants))  # Tekrarları kaldır