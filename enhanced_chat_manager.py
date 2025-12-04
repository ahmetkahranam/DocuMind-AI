"""
Gelişmiş sohbet yöneticisi - Ornekprojeden ilham alarak
Sohbet hafızası, selamlama/veda yanıtları ve kategorize edilmiş cevaplar
"""
import re
import json
import datetime
from typing import Dict, List, Any, Optional

# Güvenli import blokları
try:
    from config import config
except ImportError:
    class Config:
        pass
    config = Config()

try:
    from quer import ask_local_llm, temizle_yanit
except ImportError:
    def ask_local_llm(prompt):
        return "Import hatası nedeniyle LLM'e bağlanamıyor"
    def temizle_yanit(text):
        return text


class ConversationManager:
    """Sohbet geçmişi ve bağlam yöneticisi"""
    
    def __init__(self):
        self.conversations = {}  # user_id -> conversation_history
        self.greeting_patterns = [
            r'\b(merhaba|selam|hello|hi|hey|iyi günler|günaydın|iyi akşamlar)\b',
            r'\b(nasılsın|naber|how are you)\b'
        ]
        self.goodbye_patterns = [
            r'\b(güle güle|hoşça kal|görüşürüz|bye|goodbye|teşekkür|sağol|hoşça kalın)\b',
            r'\b(teşekkürler|thanks|thank you|tşk)\b'
        ]

    def is_greeting(self, message: str) -> bool:
        """Selamlama mesajı mı kontrol et - sadece selamlama içeren mesajları algıla"""
        message_lower = message.lower().strip()
        
        # Soru belirten kelimeler
        question_indicators = [
            'nasıl', 'ne', 'nerede', 'neden', 'kim', 'hangi', 'kaç', 'ne zaman',
            'şifre', 'parola', 'kayıt', 'belge', 'başvuru',
            'işlem', 'prosedür', 'kural', 'şart', 'koşul',
            '?'  # Soru işareti
        ]
        
        # Eğer mesajda soru belirten kelimeler varsa, bu sadece selamlama değil
        for indicator in question_indicators:
            if indicator in message_lower:
                return False
        
        # Selamlama kelimelerini kontrol et
        for pattern in self.greeting_patterns:
            if re.search(pattern, message_lower):
                # Eğer mesaj çok kısaysa (5 kelimeden az) ve sadece selamlama içeriyorsa
                words = message_lower.split()
                if len(words) <= 5:
                    return True
        
        return False

    def is_goodbye(self, message: str) -> bool:
        """Veda mesajı mı kontrol et"""
        message_lower = message.lower()
        for pattern in self.goodbye_patterns:
            if re.search(pattern, message_lower):
                return True
        return False

    def get_greeting_response(self) -> str:
        """Selamlama yanıtı"""
        return "Merhaba! Yüklediğiniz belgeler hakkında sorularınızı cevaplamaya hazırım. Size nasıl yardımcı olabilirim?"

    def get_goodbye_response(self) -> str:
        """Veda yanıtı"""
        return "Görüşmek üzere! Sorularınız için her zaman buradayım. İyi günler dilerim."

    def add_to_conversation(self, user_id: str, user_message: str, bot_response: str):
        """Sohbet geçmişine ekle"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        self.conversations[user_id].append({
            "user": user_message,
            "assistant": bot_response,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Son 10 mesajı tut (hafıza sınırı)
        if len(self.conversations[user_id]) > 10:
            self.conversations[user_id] = self.conversations[user_id][-10:]

    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Sohbet geçmişini getir"""
        return self.conversations.get(user_id, [])

    def get_conversation_context(self, user_id: str, limit: int = 3) -> str:
        """Son N mesajı bağlam olarak formatla"""
        history = self.get_conversation_history(user_id)
        if not history:
            return ""
        
        context_parts = []
        for entry in history[-limit:]:
            context_parts.append(f"Kullanıcı: {entry['user']}")
            context_parts.append(f"Asistan: {entry['assistant']}")
        
        return "\n".join(context_parts)


class QueryProcessor:
    """Basitleştirilmiş soru işleme"""
    
    def __init__(self):
        pass

    def categorize_query(self, query: str) -> str:
        """Kategorize etme kaldırıldı - her soru genel olarak işlenir"""
        return "genel"

    def get_specialized_instructions(self, category: str) -> str:
        """Genel talimatlar - kategorize etme kaldırıldı"""
        return "\nBelgelerdeki bilgileri dikkatli bir şekilde okuyun ve soruya doğrudan cevap verin. Belgede açıkça belirtilen kuralları ve bilgileri aynen aktarın."


class ResponseEvaluator:
    """Yanıt kalitesi değerlendirici"""
    
    def evaluate_response(self, response: str, query: str, sources: List[str]) -> Dict[str, Any]:
        """Yanıt kalitesini değerlendir"""
        
        # Temel metrikleri hesapla
        response_length = len(response.split())
        has_sources = len(sources) > 0
        has_specific_info = self._has_specific_information(response)
        
        # Güven skoru hesapla
        confidence_score = 0.0
        
        if response_length >= 20:  # Yeterince uzun
            confidence_score += 0.3
        if has_sources:  # Kaynak var
            confidence_score += 0.4
        if has_specific_info:  # Spesifik bilgi içeriyor
            confidence_score += 0.3
        
        # Kalite seviyesi belirle
        if confidence_score >= 0.8:
            quality_level = "Yüksek Kalite"
        elif confidence_score >= 0.5:
            quality_level = "Orta Kalite"
        else:
            quality_level = "Düşük Kalite"
        
        return {
            "confidence_score": confidence_score,
            "quality_level": quality_level,
            "response_length": response_length,
            "has_sources": has_sources,
            "has_specific_info": has_specific_info
        }
    
    def _has_specific_information(self, response: str) -> bool:
        """Spesifik bilgi içeriyor mu kontrol et"""
        specific_indicators = [
            r'\d+',  # Sayılar
            r'(tarih|saat|gün|ay|yıl)',  # Zaman ifadeleri
            r'(madde|paragraf|bent)',  # Yasal referanslar
            r'(%\d+|\d+\s*kredi)',  # Yüzde veya kredi
        ]
        
        for pattern in specific_indicators:
            if re.search(pattern, response.lower()):
                return True
        return False


# Global instances
conversation_manager = ConversationManager()
query_processor = QueryProcessor()
response_evaluator = ResponseEvaluator()
