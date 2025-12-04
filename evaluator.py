import re
from typing import Dict, List, Any, Tuple
from config import config


class ResponseEvaluator:
    """RAG sistemi yanıtlarının kalitesini değerlendiren sınıf"""

    def __init__(self):
        self.quality_metrics = {
            "relevance": 0.0,
            "completeness": 0.0,
            "accuracy": 0.0,
            "clarity": 0.0,
            "source_support": 0.0,
            "overall_score": 0.0,
        }

        # Anahtar kalite göstergeleri
        self.positive_indicators = [
            "belirtilen",
            "açıkça",
            "dokümanda",
            "yönetmeliğe göre",
            "şartlar",
            "gereklidir",
            "zorunludur",
            "tarih",
            "süre",
        ]

        self.negative_indicators = [
            "sanırım",
            "galiba",
            "muhtemelen",
            "belki",
            "tahminimce",
            "emin değilim",
            "genel olarak",
            "genellikle",
        ]

        # Akademik terimler (pozitif kalite göstergesi)
        self.academic_terms = [
            "sınav",
            "not",
            "kredi",
            "ders",
            "öğrenci",
            "mezuniyet",
            "kayıt",
            "yönetmelik",
            "komisyon",
            "değerlendirme",
            "başarı",
        ]

    def evaluate_response(
        self, response: str, query: str, sources: List[str], retrieved_docs: List[str]
    ) -> Dict[str, Any]:
        """Yanıtı kapsamlı olarak değerlendir"""

        evaluation = {
            "relevance_score": self.calculate_relevance(response, query),
            "completeness_score": self.calculate_completeness(response, query),
            "accuracy_score": self.calculate_accuracy(response, retrieved_docs),
            "clarity_score": self.calculate_clarity(response),
            "source_support_score": self.calculate_source_support(response, sources),
            "length_check": self.check_response_length(response),
            "language_quality": self.check_language_quality(response),
            "factual_consistency": self.check_factual_consistency(
                response, retrieved_docs
            ),
        }

        # Genel skor hesapla
        overall_score = self.calculate_overall_score(evaluation)
        evaluation["overall_score"] = overall_score
        evaluation["quality_level"] = self.get_quality_level(overall_score)
        evaluation["improvement_suggestions"] = self.get_improvement_suggestions(
            evaluation
        )

        return evaluation

    def calculate_relevance(self, response: str, query: str) -> float:
        """Yanıtın soruyla ne kadar ilgili olduğunu değerlendir"""
        response_lower = response.lower()
        query_lower = query.lower()

        # Query'deki anahtar kelimeleri bul
        query_words = set(re.findall(r"\w+", query_lower))
        response_words = set(re.findall(r"\w+", response_lower))

        # Ortak kelime oranı
        if not query_words:
            return 0.0

        common_words = query_words.intersection(response_words)
        relevance = len(common_words) / len(query_words)

        # Akademik terim bonusu
        academic_bonus = 0.0
        for term in self.academic_terms:
            if term in response_lower:
                academic_bonus += 0.1

        return min(1.0, relevance + academic_bonus)

    def calculate_completeness(self, response: str, query: str) -> float:
        """Yanıtın eksiksizlik durumunu değerlendir"""
        query_lower = query.lower()
        response_lower = response.lower()

        completeness_score = 0.5  # Base score

        # Soru tipi analizi
        if any(word in query_lower for word in ["nasıl", "how"]):
            # Prosedür soruları için adımlar var mı?
            if any(
                word in response_lower for word in ["adım", "önce", "sonra", "şekilde"]
            ):
                completeness_score += 0.3

        elif any(word in query_lower for word in ["ne zaman", "when", "tarih"]):
            # Zaman soruları için tarih/süre var mı?
            if re.search(r"\d+", response) or any(
                word in response_lower for word in ["tarih", "süre", "gün"]
            ):
                completeness_score += 0.3

        elif any(word in query_lower for word in ["kaç", "how many"]):
            # Sayısal sorular için rakam var mı?
            if re.search(r"\d+", response):
                completeness_score += 0.3

        # Yanıt uzunluğu kontrolü
        word_count = len(response.split())
        if word_count >= 20:  # Yeterli detay
            completeness_score += 0.2

        return min(1.0, completeness_score)

    def calculate_accuracy(self, response: str, retrieved_docs: List[str]) -> float:
        """Yanıtın belgelerle tutarlılığını kontrol et"""
        if not retrieved_docs:
            return 0.0

        response_lower = response.lower()
        accuracy_score = 0.0
        total_checks = 0

        # Yanıttaki sayısal bilgileri kontrol et
        response_numbers = re.findall(r"\d+", response)

        for doc in retrieved_docs[:3]:  # İlk 3 dokümanı kontrol et
            doc_lower = doc.lower()
            doc_numbers = re.findall(r"\d+", doc)

            # Sayısal tutarlılık kontrolü
            for num in response_numbers:
                total_checks += 1
                if num in doc_numbers:
                    accuracy_score += 1.0

        # Temel accuracy hesaplama
        if total_checks > 0:
            numerical_accuracy = accuracy_score / total_checks
        else:
            numerical_accuracy = 0.5  # Default score

        # Belirsizlik ifadeleri cezası
        uncertainty_penalty = 0.0
        for indicator in self.negative_indicators:
            if indicator in response_lower:
                uncertainty_penalty += 0.1

        # Kesinlik ifadeleri bonusu
        certainty_bonus = 0.0
        for indicator in self.positive_indicators:
            if indicator in response_lower:
                certainty_bonus += 0.1

        final_accuracy = numerical_accuracy + certainty_bonus - uncertainty_penalty
        return max(0.0, min(1.0, final_accuracy))

    def calculate_clarity(self, response: str) -> float:
        """Yanıtın netlik durumunu değerlendir"""
        clarity_score = 0.5  # Base score

        # Cümle yapısı analizi
        sentences = response.split(".")
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(
            len(sentences), 1
        )

        # Optimal cümle uzunluğu (15-25 kelime)
        if 15 <= avg_sentence_length <= 25:
            clarity_score += 0.2
        elif avg_sentence_length > 35:
            clarity_score -= 0.2

        # Noktalama kontrolü
        if response.count(".") >= 2:  # En az 2 cümle
            clarity_score += 0.1

        # Türkçe dilbilgisi göstergeleri
        if any(
            word in response.lower() for word in ["için", "ile", "ve", "ancak", "fakat"]
        ):
            clarity_score += 0.1

        # Çok uzun paragraf cezası
        if len(response) > 500:
            clarity_score -= 0.1

        return max(0.0, min(1.0, clarity_score))

    def calculate_source_support(self, response: str, sources: List[str]) -> float:
        """Yanıtın kaynaklarla ne kadar desteklendiğini kontrol et"""
        if not sources:
            return 0.0

        support_score = 0.5  # Base score

        # Kaynak sayısı
        if len(sources) >= 2:
            support_score += 0.2
        elif len(sources) >= 1:
            support_score += 0.1

        # Yanıtta kaynak referansı var mı?
        response_lower = response.lower()
        if any(
            word in response_lower for word in ["belge", "dokuman", "kaynak", "göre"]
        ):
            support_score += 0.2

        # Spesifik belge adı referansı
        for source in sources:
            if (
                source.lower().replace(".pdf", "").replace(".docx", "")
                in response_lower
            ):
                support_score += 0.1

        return min(1.0, support_score)

    def check_response_length(self, response: str) -> Dict[str, Any]:
        """Yanıt uzunluğunu kontrol et"""
        word_count = len(response.split())
        char_count = len(response)

        return {
            "word_count": word_count,
            "char_count": char_count,
            "too_short": word_count < config.MIN_ANSWER_LENGTH,
            "too_long": word_count > config.MAX_ANSWER_LENGTH,
            "optimal_length": config.MIN_ANSWER_LENGTH
            <= word_count
            <= config.MAX_ANSWER_LENGTH,
        }

    def check_language_quality(self, response: str) -> Dict[str, Any]:
        """Dil kalitesini kontrol et"""
        issues = []
        score = 1.0

        # Tekrarlayan kelimeler
        words = response.lower().split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        repeated_words = [
            word for word, freq in word_freq.items() if freq > 3 and len(word) > 3
        ]
        if repeated_words:
            issues.append(f"Tekrarlayan kelimeler: {repeated_words[:3]}")
            score -= 0.2

        # Çok uzun cümleler
        sentences = response.split(".")
        long_sentences = [s for s in sentences if len(s.split()) > 40]
        if long_sentences:
            issues.append("Çok uzun cümleler mevcut")
            score -= 0.1

        # Belirsizlik ifadeleri
        uncertainty_count = sum(
            1 for indicator in self.negative_indicators if indicator in response.lower()
        )
        if uncertainty_count > 2:
            issues.append("Çok fazla belirsizlik ifadesi")
            score -= 0.3

        return {
            "score": max(0.0, score),
            "issues": issues,
            "uncertainty_count": uncertainty_count,
        }

    def check_factual_consistency(
        self, response: str, retrieved_docs: List[str]
    ) -> Dict[str, Any]:
        """Faktüel tutarlılığı kontrol et"""
        if not retrieved_docs:
            return {"score": 0.0, "issues": ["Kaynak belge yok"]}

        issues = []
        score = 0.8  # Base score

        # Yanıttaki rakamları kontrol et
        response_numbers = re.findall(r"\d+", response)
        doc_numbers = []
        for doc in retrieved_docs:
            doc_numbers.extend(re.findall(r"\d+", doc))

        inconsistent_numbers = []
        for num in response_numbers:
            if num not in doc_numbers:
                inconsistent_numbers.append(num)

        if inconsistent_numbers:
            issues.append(f"Belgede bulunmayan rakamlar: {inconsistent_numbers}")
            score -= 0.3

        # Yanıtta belirtilen fakat belgelerde olmayan terimler
        response_terms = set(re.findall(r"\b\w{4,}\b", response.lower()))
        doc_terms = set()
        for doc in retrieved_docs:
            doc_terms.update(re.findall(r"\b\w{4,}\b", doc.lower()))

        new_terms = response_terms - doc_terms
        if len(new_terms) > 5:  # Çok fazla yeni terim
            issues.append("Belgelerde bulunmayan çok fazla terim kullanılmış")
            score -= 0.2

        return {
            "score": max(0.0, score),
            "issues": issues,
            "inconsistent_numbers": inconsistent_numbers,
        }

    def calculate_overall_score(self, evaluation: Dict[str, Any]) -> float:
        """Genel kalite skorunu hesapla"""
        weights = {
            "relevance_score": 0.25,
            "completeness_score": 0.20,
            "accuracy_score": 0.25,
            "clarity_score": 0.15,
            "source_support_score": 0.15,
        }

        overall = 0.0
        for metric, weight in weights.items():
            overall += evaluation.get(metric, 0.0) * weight

        # Dil kalitesi cezası
        lang_quality = evaluation.get("language_quality", {})
        overall *= lang_quality.get("score", 1.0)

        # Faktüel tutarlılık cezası
        factual = evaluation.get("factual_consistency", {})
        overall *= factual.get("score", 1.0)

        return max(0.0, min(1.0, overall))

    def get_quality_level(self, score: float) -> str:
        """Skor bazında kalite seviyesi"""
        if score >= 0.8:
            return "Mükemmel"
        elif score >= 0.6:
            return "İyi"
        elif score >= 0.4:
            return "Orta"
        elif score >= 0.2:
            return "Zayıf"
        else:
            return "Çok Zayıf"

    def get_improvement_suggestions(self, evaluation: Dict[str, Any]) -> List[str]:
        """İyileştirme önerileri"""
        suggestions = []

        if evaluation.get("relevance_score", 0) < 0.5:
            suggestions.append("Soruyla daha ilgili bilgiler verin")

        if evaluation.get("completeness_score", 0) < 0.5:
            suggestions.append("Daha detaylı ve eksiksiz cevap verin")

        if evaluation.get("accuracy_score", 0) < 0.5:
            suggestions.append("Belgelerle tutarlı bilgiler verin")

        if evaluation.get("clarity_score", 0) < 0.5:
            suggestions.append("Daha net ve anlaşılır yazın")

        if evaluation.get("source_support_score", 0) < 0.5:
            suggestions.append("Kaynak belgelerden daha fazla yararlanın")

        length_check = evaluation.get("length_check", {})
        if length_check.get("too_short"):
            suggestions.append("Yanıtı daha detaylandırın")
        elif length_check.get("too_long"):
            suggestions.append("Yanıtı daha kısa ve öz yapın")

        lang_quality = evaluation.get("language_quality", {})
        if lang_quality.get("uncertainty_count", 0) > 2:
            suggestions.append("Daha kesin ifadeler kullanın")

        return suggestions