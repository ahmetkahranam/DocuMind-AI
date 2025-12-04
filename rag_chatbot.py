import chromadb
from quer import ask_local_llm, temizle_yanit
from config import config
from query_processor import QueryProcessor
from hybrid_retriever import HybridRetriever
from evaluator import ResponseEvaluator
import logging
import re
from typing import Dict, List, Any, Optional

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedRAGChatbot:
    """Gelişmiş RAG Chatbot sistemi"""

    def __init__(self, chroma_path: str = "./chroma"):
        self.retriever = HybridRetriever(chroma_path)
        self.query_processor = QueryProcessor()
        self.evaluator = ResponseEvaluator()
        
        # Conversation history için
        self.conversation_history = []  # [(question, answer, timestamp), ...]
        self.max_history_length = 5  # Son 5 soru-cevap çiftini hatırla

        logger.info("🤖 Gelişmiş RAG Chatbot başlatıldı!")

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Kullanıcı sorgusunu kapsamlı şekilde işle"""
        try:
            # 1. Context-aware query expansion
            expanded_query = self._expand_query_with_context(user_query)
            
            # 2. Query preprocessing
            processed_query = self.query_processor.process_query(expanded_query)
            logger.info(f"📝 İşlenmiş sorgu kategorisi: {processed_query['category']}")

            # 3. Advanced retrieval
            retrieval_result = self.retriever.advanced_retrieve(
                expanded_query, n_results=config.DEFAULT_N_RESULTS
            )

            if not retrieval_result["results"]:
                return self._handle_no_results(user_query)

            # 3.5. Context-aware boosting - conversation history'deki belgeleri öne çıkar
            boosted_results = self._apply_conversation_context_boost(retrieval_result["results"], user_query)

            # 4. Filter by similarity threshold
            filtered_results = self.retriever.filter_by_similarity_threshold(
                boosted_results
            )

            if not filtered_results:
                return self._handle_low_similarity(
                    user_query, retrieval_result["results"]
                )

            # 4. Context preparation
            context_info = self._prepare_context(filtered_results, processed_query)

            # 5. Generate response
            response_data = self._generate_response(
                user_query, context_info, processed_query
            )

            # 6. Evaluate response quality
            evaluation = self._evaluate_response(
                response_data["response"],
                user_query,
                context_info["sources"],
                context_info["documents"],
            )

            # 7. Prepare final result
            # Sadece gerçekten kullanılan ilk source'u döndür (en yüksek skorlu)
            result = {
                "response": response_data["response"],
                "sources": context_info["sources"][:1],  # İlk source (en alakalı)
                "confidence": evaluation["overall_score"],
                "quality_level": evaluation["quality_level"],
                "query_analysis": processed_query,
                "retrieval_info": {
                    "total_found": len(retrieval_result["results"]),
                    "after_filtering": len(filtered_results),
                    "best_score": (
                        filtered_results[0]["combined_score"] if filtered_results else 0
                    ),
                },
                "evaluation": evaluation,
            }

            # 8. Conversation history'ye ekle
            self._add_to_conversation_history(user_query, response_data["response"])

            return result

        except Exception as e:
            logger.error(f"❌ Query işleme hatası: {e}")
            return self._handle_error(user_query, str(e))

    def _expand_query_with_context(self, user_query: str) -> str:
        """Conversation history kullanarak sorguyu genişlet"""
        
        # Kısa sorguları veya referans içeren sorguları context ile genişlet
        query_words = user_query.split()
        
        if len(query_words) <= 6 and self.conversation_history:  # 6 kelime veya daha az
            
            # Son soru-cevap çiftini al
            last_qa = self.conversation_history[-1]
            last_question = last_qa[0]
            
            # Referans kelimeler - Türkçe'de yaygın
            reference_words = ['bu', 'şu', 'o', 'bunun', 'şunun', 'onun', 'bunu', 'şunu', 'onu', 
                             'için', 'hakkında', 'konusunda', 'ile ilgili', 'bahar', 'güz', 'yarıyıl',
                             'dönemi', 'dönem', 'sınıfım', 'yapabilir', 'miyim', 'mıyım', 'mi', 'mı', 
                             'peki', 'ya', 'ayrıca', 'öte yandan', 'bir de', 'diğer', 'sonra']
            
            # Mevcut sorgu belirsiz/referans içerir mi?
            has_reference = any(word in user_query.lower() for word in reference_words)
            is_vague = len(query_words) <= 4
            
            if has_reference or is_vague:
                # Son sorudaki anahtar terimleri çıkar (çok spesifik olanları)
                last_keywords = self._extract_query_keywords(last_question)
                
                # Önemli domain-specific terimleri filtrele
                important_terms = []
                for word in last_keywords:
                    if len(word) > 3 and word not in ['için', 'neden', 'nasıl', 'nedir', 'zaman', 'yapmak', 'istiyorum']:
                        important_terms.append(word)
                
                # Son cevaptan da kritik terimleri çıkar
                last_answer = last_qa[1]
                answer_keywords = self._extract_query_keywords(last_answer)
                for word in answer_keywords:
                    if len(word) > 4 and word not in important_terms and word not in ['belge', 'dokuman', 'bilgi', 'konuda', 'için']:
                        important_terms.append(word)
                
                # Context relevance check - eğer mevcut soru tamamen farklı ise expand etme
                current_keywords = self._extract_query_keywords(user_query)
                
                # Eğer mevcut soruda çok spesifik ve uzun terimler varsa ve 
                # son soruyla hiç overlap yoksa expand etme (daha esnek kontrol)
                if len(current_keywords) > 2:  # En az 3 keyword varsa kontrol et
                    # Çok spesifik current keywords (uzun ve akademik olmayan)
                    very_specific = [w for w in current_keywords if len(w) > 6 and w not in [
                        'prosedür', 'belgeleme', 'değerlendirme', 'yönerge', 'yönerges',
                        'başarı', 'işlem', 'gereklilik', 'muafiyet'
                    ]]
                    
                    if very_specific:  # Çok spesifik terimler var
                        # Semantic overlap kontrolü - daha esnek
                        semantic_overlap = any(
                            term in last_question.lower() or 
                            any(last_word in term for last_word in last_keywords if len(last_word) > 3)
                            for term in very_specific
                        )
                        if not semantic_overlap:
                            # Tamamen farklı konu, expand etme
                            logger.info(f"🚫 Farklı konu tespit edildi, expand yapılmıyor: {very_specific}")
                            return user_query
                
                # En fazla 3 önemli terim ekle
                context_terms = important_terms[:3]
                
                if context_terms:
                    expanded = f"{user_query} {' '.join(context_terms)}"
                    logger.info(f"🔗 Query genişletildi: '{user_query}' → '{expanded}'")
                    return expanded
        
        return user_query

    def _apply_conversation_context_boost(self, results: List[Dict[str, Any]], user_query: str) -> List[Dict[str, Any]]:
        """Conversation history'de kullanılan belgelere ve konulara ekstra boost ver - GENEL SİSTEM"""
        if not self.conversation_history or not results:
            return results
        
        # Vague/belirsiz sorguları tespit et (conversation context gerektiren)
        # Daha esnek koşullar - sadece kelime sayısı değil, conversation pattern'i de önemli
        needs_context = False
        
        # Koşul 1: Kısa sorgular (≤10 kelime)
        if len(user_query.split()) <= 10:
            needs_context = True
            
        # Koşul 2: Belirsiz/eksik bilgi içeren sorgular
        vague_patterns = [
            r'\b(bu|şu|o)\b.*\b(nedir|nasıl|ne|hangi)\b',  # "bu nedir", "şu nasıl" 
            r'\b(peki|ya|ayrıca)\b',                        # "peki", "ya", "ayrıca"
            r'\b(görev|kurul|sistem|belge)\b.*\bnedir\b',   # "...nedir" ile biten sorular
            r'\b(yapabilir|olabilir|mümkün)\s+(mi|mı)\b',   # "yapabilir mi" türü sorular
        ]
        
        for pattern in vague_patterns:
            if re.search(pattern, user_query.lower()):
                needs_context = True
                break
                
        if needs_context and self.conversation_history:
            
            # Son 2 conversation'dan anahtar terimleri çıkar
            context_keywords = set()
            recent_sources = set()
            
            for question, answer, timestamp in self.conversation_history[-2:]:
                # Sorulardan anahtar kelimeler
                q_keywords = self._extract_query_keywords(question)
                context_keywords.update(q_keywords)
                
                # Cevaplardan da önemli terimleri çıkar (fakülte adları, program isimleri vs.)
                a_keywords = self._extract_context_keywords_from_answer(answer)
                context_keywords.update(a_keywords)
            
            # Son kullanılan belgeyi tespit et (çok önemli!)
            last_used_sources = set()
            
            # Conversation history'den pattern matching ile kaynak tespit et
            for question, answer, timestamp in self.conversation_history[-2:]:
                # Cevaptan domain pattern'lerini tespit et
                combined_text = (question + " " + answer).lower()
                
                # Domain-specific pattern matching
                if any(term in combined_text for term in ['tercüme', 'senaryo', 'tıp fakültesi', 'tıp eğitimi']):
                    last_used_sources.add('179492.pdf')  # Tıp Fakültesi belgesi
                elif any(term in combined_text for term in ['diş hekimliği', 'diş hekimliği fakültesi']):
                    last_used_sources.add('139037.pdf')  # Diş hekimliği belgesi
                elif any(term in combined_text for term in ['yabancı dil', 'dil eğitimi', 'muafiyet']):
                    last_used_sources.add('147419.pdf')  # Yabancı dil belgesi
                elif any(term in combined_text for term in ['başarı değerlendirme', 'yüzde on', '%10']):
                    last_used_sources.add('82916.pdf')   # Başarı değerlendirme belgesi
                elif any(term in combined_text for term in ['yatay geçiş', 'transfer', 'nakil']):
                    # Yatay geçiş birden fazla belgede olabilir, context'e göre karar ver
                    if 'diş hekimliği' in combined_text:
                        last_used_sources.add('139037.pdf')
                    else:
                        last_used_sources.add('173204.pdf')  # Genel yatay geçiş belgesi
            
            # Context keywords varsa boost uygula
            if context_keywords:
                logger.info(f"🔗 Conversation context boost uygulanıyor - Context keywords: {list(context_keywords)[:5]}...")
                
                boosted_results = []
                boosted_count = 0
                
                for result in results:
                    source_file = result.get('metadata', {}).get('source_file', '')
                    doc_content = result.get('document', '').lower()
                    
                    # Bu belge conversation context'e ne kadar uygun?
                    relevance_score = self._calculate_context_relevance(doc_content, context_keywords)
                    
                    # Eğer bu belge son kullanılan belgelerden biriyse ekstra boost
                    extra_boost = 1.0
                    for last_source in last_used_sources:
                        if last_source in source_file:
                            extra_boost = 1.8  # %80 ekstra boost
                            logger.info(f"🎯 Son kullanılan belge tespit edildi: {source_file} - ekstra boost veriliyor")
                            break
                    
                    if relevance_score > 0.3:  # %30'dan fazla alakalı ise boost ver
                        boosted_result = result.copy()
                        original_score = boosted_result.get('combined_score', 0)
                        # Relevance score'a göre değişken boost (1.2x - 1.8x) + ekstra boost
                        boost_factor = (1.2 + (relevance_score * 0.6)) * extra_boost
                        boosted_result['combined_score'] = original_score * boost_factor
                        boosted_results.append(boosted_result)
                        boosted_count += 1
                        logger.info(f"🚀 Context boost: {source_file} - {original_score:.3f} → {boosted_result['combined_score']:.3f} (relevance: {relevance_score:.3f}, extra: {extra_boost:.1f}x)")
                    else:
                        boosted_results.append(result)
                
                # Score'a göre yeniden sırala
                boosted_results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
                
                logger.info(f"🔗 Conversation context boost tamamlandı: {boosted_count} belge boost edildi")
                
                return boosted_results
        
        return results

    def _extract_context_keywords_from_answer(self, answer: str) -> List[str]:
        """Cevaplardan önemli context anahtar kelimelerini çıkar"""
        import re
        
        keywords = []
        text_lower = answer.lower()
        
        # Fakülte/program isimleri
        faculty_patterns = [
            r'(\w+)\s+fakültesi?',
            r'(\w+)\s+bölümü',
            r'(\w+)\s+programı',
            r'(\w+)\s+yüksekokulu',
            r'(\w+)\s+enstitüsü'
        ]
        
        for pattern in faculty_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if len(match) > 3:  # Çok kısa kelimeler hariç
                    keywords.append(match)
        
        # Önemli genel terimler
        important_terms = [
            'belge', 'başvuru', 'işlem', 'prosedür', 'kural', 'koşul', 'süreç',
            'gerekli', 'şart', 'onay', 'değerlendirme', 'başarı', 'form',
            'yönetmelik', 'muafiyet', 'nakil', 'transfer', 'sertifika', 'kayıt',
            'dönem', 'süre', 'güncelleme', 'revizyon', 'kontrol', 'uygunluk'
        ]
        
        for term in important_terms:
            if term in text_lower:
                keywords.append(term)
        
        return list(set(keywords))  # Tekrarları kaldır

    def _calculate_context_relevance(self, document: str, context_keywords: set) -> float:
        """Bir belgenin conversation context'e ne kadar alakalı olduğunu hesapla"""
        if not context_keywords:
            return 0.0
        
        doc_lower = document.lower()
        
        # Context keywords'ün belgede kaç tanesi var?
        found_keywords = []
        for keyword in context_keywords:
            keyword_lower = keyword.lower()
            if len(keyword_lower) > 2:  # Çok kısa kelimeler hariç
                if keyword_lower in doc_lower:
                    found_keywords.append(keyword_lower)
        
        # Relevance score = bulunan keyword oranı
        if len(context_keywords) > 0:
            relevance = len(found_keywords) / len(context_keywords)
        else:
            relevance = 0.0
        
        # Bonus: Eğer aynı belgede birden fazla context keyword varsa ek puan
        if len(found_keywords) > 1:
            relevance += 0.2
        
        return min(relevance, 1.0)  # Max 1.0

    def _add_to_conversation_history(self, question: str, answer: str):
        """Conversation history'ye soru-cevap çifti ekle"""
        import time
        
        # Yeni soru-cevap çiftini ekle
        self.conversation_history.append((question, answer, time.time()))
        
        # History uzunluğunu sınırla
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]

    def _prepare_context(
        self, results: List[Dict[str, Any]], processed_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retrieval sonuçlarından context hazırla"""

        context_parts = []
        sources = []  # Set yerine list - sıralamayı koru
        documents = []
        user_query = processed_query.get('original_query', processed_query.get('query', ''))

        for i, result in enumerate(results[: config.DEFAULT_N_RESULTS], 1):
            doc = result["document"]
            metadata = result.get("metadata", {})
            score = result.get("combined_score", 0)

            # Document relevans kontrolü - alakasız dökümanları filtrele
            if not self._is_document_relevant_to_query(doc, user_query):
                continue

            # Document preprocessing - user_query ile birlikte
            clean_doc = self._clean_document_for_context(doc, user_query)
            documents.append(clean_doc)

            # Source tracking - sıralı ve tekrarsız
            source_file = metadata.get("source_file", f"Belge_{i}")
            if source_file not in sources:  # Duplicate check
                sources.append(source_file)

            # Context formatting
            context_parts.append(
                {
                    "index": i,
                    "content": clean_doc,
                    "source": source_file,
                    "score": score,
                    "chunk_index": metadata.get("chunk_index", 0),
                }
            )

        # Generate rich context
        formatted_context = self._format_context_for_llm(context_parts, processed_query)

        return {
            "formatted_context": formatted_context,
            "sources": sources,  # Artık list olarak döndür
            "documents": documents,
            "context_parts": context_parts,
        }

    def _clean_document_for_context(self, document: str, user_query: str = "") -> str:
        """Dokümanı context için akıllıca temizle"""
        # Fazla boşlukları temizle
        clean_doc = " ".join(document.split())
        words = clean_doc.split()
        max_words = config.MAX_CONTEXT_LENGTH // 5  # Yaklaşık kelime başına 5 karakter

        # Eğer döküman kısa ise direkt döndür
        if len(words) <= max_words:
            return clean_doc

        # Akıllı kesme: Sorgu anahtar kelimelerini içeren kısmı bul
        if user_query:
            query_keywords = self._extract_query_keywords(user_query)
            
            # Anahtar kelimelerin geçtiği yerleri bul
            keyword_positions = []
            doc_lower = clean_doc.lower()
            
            for keyword in query_keywords:
                keyword_lower = keyword.lower()
                start = 0
                while True:
                    pos = doc_lower.find(keyword_lower, start)
                    if pos == -1:
                        break
                    # Kelime pozisyonunu hesapla
                    word_pos = len(doc_lower[:pos].split())
                    keyword_positions.append(word_pos)
                    start = pos + 1
            
            if keyword_positions:
                # En erken anahtar kelime pozisyonunu bul
                earliest_keyword = min(keyword_positions)
                
                # Context'i anahtar kelimeden önce ve sonra dengeli dağıt
                context_before = max_words // 3  # 1/3'ü önceki kısım
                context_after = max_words - context_before  # 2/3'ü sonraki kısım
                
                start_pos = max(0, earliest_keyword - context_before)
                end_pos = min(len(words), start_pos + max_words)
                
                # Eğer son kısım kısa kalırsa baştan daha fazla al
                if end_pos - start_pos < max_words:
                    start_pos = max(0, end_pos - max_words)
                
                selected_words = words[start_pos:end_pos]
                prefix = "..." if start_pos > 0 else ""
                suffix = "..." if end_pos < len(words) else ""
                
                return f"{prefix}{' '.join(selected_words)}{suffix}"
        
        # Fallback: Sadece baştan al
        return " ".join(words[:max_words]) + "..."

    def _is_document_relevant_to_query(self, document: str, user_query: str) -> bool:
        """Dökümanın sorguyla alakalı olup olmadığını kontrol et"""
        doc_lower = document.lower()
        
        # Genel anahtar kelime kontrolü
        query_keywords = self._extract_query_keywords(user_query)
        if not query_keywords:
            return True  # Anahtar kelime yoksa tüm dökümanları al
            
        # En az bir anahtar kelime geçmeli
        keyword_matches = sum(1 for keyword in query_keywords if keyword in doc_lower)
        
        # Eğer çok uzun döküman ise (>10000 karakter) daha esnek ol
        if len(document) > 10000:
            return keyword_matches > 0  # En az 1 match yeterli
        else:
            return keyword_matches > 0

    def _format_context_for_llm(
        self, context_parts: List[Dict[str, Any]], processed_query: Dict[str, Any]
    ) -> str:
        """LLM için context'i formatla"""

        context_lines = []

        for part in context_parts:
            source_info = f"[{part['source']}]"
            content = part["content"]
            score_info = f"(Uygunluk: {part['score']:.2f})"

            context_lines.append(
                f"{part['index']}. {source_info} {content} {score_info}"
            )

        return "\n\n".join(context_lines)

    def _generate_response(
        self,
        user_query: str,
        context_info: Dict[str, Any],
        processed_query: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Gelişmiş prompt ile yanıt üret"""

        # Query kategorisine göre özelleştirilmiş prompt
        specialized_instructions = self._get_specialized_instructions(
            processed_query["category"]
        )

        # Tek soruya odaklanan prompt oluştur
        focused_system_prompt = config.SYSTEM_PROMPT + "\n" + specialized_instructions + """

ÖNEMLI: Sadece kullanıcının şu anda sorduğu soruya cevap ver. Önceki sorular veya konularla ilgili bilgi verme.
Bu sorguya özgü ve kesin bir yanıt ver. Başka konulara değinme."""

        # Ana prompt oluştur
        prompt = config.RAG_PROMPT_TEMPLATE.format(
            system_prompt=focused_system_prompt,
            question=user_query,
            context=context_info["formatted_context"],
        )

        # LLM'den yanıt al
        raw_response = ask_local_llm(prompt, model=config.LLM_MODEL)
        clean_response = temizle_yanit(raw_response)

        # Yanıt post-processing - tek soruya odaklanarak
        processed_response = self._post_process_response(
            clean_response, context_info["sources"], user_query
        )

        return {
            "response": processed_response,
            "raw_response": raw_response,
            "prompt_used": prompt,
        }

    def _get_specialized_instructions(self, query_category: str) -> str:
        """Query kategorisine göre özel talimatlar"""
        instructions = {
            "procedure": "\nProsedür sorularında adım adım açıklama yap. Sıralı işlemler ver.",
            "temporal": "\nTarih ve zaman bilgilerini kesin olarak belirt. 'yaklaşık' gibi belirsiz ifadeler kullanma.",
            "quantitative": "\nSayısal bilgileri tam olarak ver. Belirsizlik varsa bunu açıkça belirt.",
            "definition": "\nTanımları net ve anlaşılır şekilde yap. Örnekler ver.",
            "explanation": "\nSebep-sonuç ilişkilerini açıkla. Mantıklı gerekçeler sun.",
            "location": "\nYer bilgilerini spesifik olarak belirt.",
            "general": "\nKapsamlı ve düzenli bir açıklama yap.",
        }

        return instructions.get(query_category, instructions["general"])

    def _post_process_response(self, response: str, sources: List[str], user_query: str = None) -> str:
        """Yanıtı son işleme tabi tut"""

        # Kaynak bilgilerini temizle - LLM'den gelen kaynak referanslarını kaldır
        import re
        
        # Eğer bu bir fallback response ise, sadece temel temizlik yap
        if response == config.FALLBACK_RESPONSE or "belgelerimde yeterli bilgi bulunmuyor" in response:
            # Sadece temel temizlik
            response = re.sub(r'\s+', ' ', response)
            return response.strip()
        
        # Normal cevaplar için sadece zararlı dosya referanslarını temizle
        # Sadece cümle sonundaki dosya adlarını ve açık kaynak referanslarını temizle
        
        # 1. Kaynak referanslarını kapsamlı temizleme
        response = re.sub(r'\s*Kaynak:\s*\[.*?\].*?$', '', response, flags=re.IGNORECASE | re.MULTILINE)
        response = re.sub(r'\s*Kaynak:\s*.*?\.pdf.*?$', '', response, flags=re.IGNORECASE | re.MULTILINE)
        response = re.sub(r'\s*Kaynak:\s*.*?\.docx.*?$', '', response, flags=re.IGNORECASE | re.MULTILINE)
        response = re.sub(r'\s*Kaynak belge:\s*.*?$', '', response, flags=re.IGNORECASE | re.MULTILINE)
        response = re.sub(r'\s*Kaynaklar:\s*.*?$', '', response, flags=re.IGNORECASE | re.MULTILINE)
        
        # 2. Köşeli parantezlerle çevrili dosya referansları
        response = re.sub(r'\s*\[.*?\.pdf\].*?$', '', response, flags=re.IGNORECASE | re.MULTILINE)
        response = re.sub(r'\s*\[.*?\.docx\].*?$', '', response, flags=re.IGNORECASE | re.MULTILINE)
        
        # 3. Özel dosya adı formatlarını temizle
        response = re.sub(r'\s*\d+-\d+-\d+_[A-Za-z0-9_-]+\.pdf\s*', ' ', response, flags=re.IGNORECASE)
        response = re.sub(r'\s*[A-Z]+\.\d+\.[A-Z]+\.\d+.*?\.pdf\s*', ' ', response, flags=re.IGNORECASE)
        
        # 4. Eksik parantezleri ve noktalama işaretlerini temizle
        response = re.sub(r'\s*\($\s*', '', response, flags=re.MULTILINE)
        response = re.sub(r'\s*\)$\s*', '', response, flags=re.MULTILINE)
        response = re.sub(r'\s*\[\s*$', '', response, flags=re.MULTILINE)
        response = re.sub(r'\s*\]\s*$', '', response, flags=re.MULTILINE)
        response = re.sub(r'\s*[,;:]\s*$', '', response, flags=re.MULTILINE)
        
        # 5. Çoklu boşlukları ve satır sonlarını düzelt
        response = re.sub(r'\s+', ' ', response)
        response = re.sub(r'\s*\n\s*', '\n', response)
        
        # 6. Tekrar eden nokta işaretlerini düzelt
        response = re.sub(r'\.{2,}', '.', response)
        
        # 7. Cümle bitişlerini düzelt
        response = re.sub(r'\s*\.\s*', '. ', response)
        response = response.strip()
        
        # 8. Çok kısa yanıtları genişlet
        if len(response) < config.MIN_ANSWER_LENGTH:
            response += " Bu konuda daha detaylı bilgi için ilgili belgeleri inceleyebilirsiniz."

        return response.strip()

    def _filter_response_for_single_query(self, response: str, user_query: str) -> str:
        """Yanıtı tek soruya odaklayacak şekilde filtrele"""
        
        # Önce alakasız ifadeleri temizle
        response = self._remove_irrelevant_phrases(response, user_query)
        
        # Eğer yanıt çok kısa kaldıysa, LLM'den gelen orijinal yanıtı kullan
        if len(response.strip()) < 50:
            return response
        
        # Kullanıcının sorusundaki anahtar kelimeleri çıkar
        query_keywords = self._extract_query_keywords(user_query)
        
        # Yanıtı cümlelere böl (nokta, ünlem, soru işaretiyle)
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]  # Boş cümleleri temizle
        
        filtered_sentences = []
        
        # İlk iki cümleyi her zaman dahil et (genellikle doğru cevap)
        if sentences:
            filtered_sentences.extend(sentences[:2])
        
        # Diğer cümleleri relevans kontrolünden geçir
        for sentence in sentences[2:]:
            if self._is_sentence_relevant_to_query(sentence, query_keywords, user_query):
                filtered_sentences.append(sentence)
            else:
                # İlgisiz cümle bulunduğunda dur (çoklu konu yanıtını önle)
                break
        
        # Cümleleri doğru şekilde birleştir
        if filtered_sentences:
            filtered_response = '. '.join(filtered_sentences)
            if not filtered_response.endswith('.'):
                filtered_response += '.'
        else:
            filtered_response = response  # Fallback
        
        return filtered_response.strip()

    def _extract_query_keywords(self, query: str) -> list:
        """Sorgudan anahtar kelimeleri çıkar"""
        # Türkçe stop words
        stop_words = {'ve', 'ile', 'için', 'de', 'da', 'bir', 'bu', 'şu', 'o', 'ben', 'sen', 'biz', 'siz', 'onlar',
                     'nasıl', 'ne', 'nedir', 'kim', 'nerede', 'neden', 'niçin', 'hangi', 'kaç', 'ne zaman'}
        
        words = query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords

    def _is_sentence_relevant_to_query(self, sentence: str, query_keywords: list, user_query: str) -> bool:
        """Cümlenin sorguyla alakalı olup olmadığını kontrol et"""
        sentence_lower = sentence.lower()
        
        # Anahtar kelime match kontrolü
        keyword_matches = sum(1 for keyword in query_keywords if keyword in sentence_lower)
        
        # Eğer hiç anahtar kelime yoksa alakasız
        return keyword_matches > 0

    def _remove_irrelevant_phrases(self, response: str, user_query: str) -> str:
        """Alakasız ifadeleri temizle"""
        
        # Genel alakasız başlangıçları temizle
        irrelevant_starts = [
            r'^[^.]*belgede[^.]*kurallar[^.]*\.',
            r'^[^.]*ancak[^.]*\.',
            r'^[^.]*eğer[^.]*\.'
        ]
        
        for pattern in irrelevant_starts:
            response = re.sub(pattern, '', response, flags=re.IGNORECASE)
        
        # Çoklu boşlukları ve nokta hatalarını düzelt
        response = re.sub(r'\s+', ' ', response)
        response = re.sub(r'\.+', '.', response)
        response = re.sub(r'\s*\.\s*', '. ', response)
        
        # Başında/sonunda gereksiz boşluk ve nokta temizle
        response = response.strip(' .')
        
        # Eğer cümle noktayla bitmiyorsa ekle
        if response and not response.endswith('.'):
            response += '.'
            
        return response

    def _evaluate_response(
        self, response: str, query: str, sources: List[str], documents: List[str]
    ) -> Dict[str, Any]:
        """Yanıt kalitesini değerlendir"""
        return self.evaluator.evaluate_response(response, query, sources, documents)

    def _handle_no_results(self, query: str) -> Dict[str, Any]:
        """Sonuç bulunamadığında"""
        return {
            "response": config.FALLBACK_RESPONSE,
            "sources": [],
            "confidence": 0.0,
            "quality_level": "Bilgi Yok",
            "query_analysis": self.query_processor.process_query(query),
            "retrieval_info": {"total_found": 0, "after_filtering": 0, "best_score": 0},
            "evaluation": {
                "overall_score": 0.0,
                "improvement_suggestions": ["Daha spesifik soru sorun"],
            },
        }

    def _handle_low_similarity(
        self, query: str, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Düşük benzerlik skorlarında"""
        best_score = results[0]["combined_score"] if results else 0

        response = config.FALLBACK_RESPONSE

        return {
            "response": response,
            "sources": [],
            "confidence": best_score,
            "quality_level": "Düşük Güven",
            "query_analysis": self.query_processor.process_query(query),
            "retrieval_info": {
                "total_found": len(results),
                "after_filtering": 0,
                "best_score": best_score,
            },
            "evaluation": {
                "overall_score": 0.2,
                "improvement_suggestions": ["Sorguyu yeniden formüle edin"],
            },
        }

    def _handle_error(self, query: str, error_msg: str) -> Dict[str, Any]:
        """Hata durumunda"""
        return {
            "response": f"Üzgünüm, sorunuzu işlerken bir hata oluştu: {error_msg}",
            "sources": [],
            "confidence": 0.0,
            "quality_level": "Hata",
            "error": error_msg,
            "evaluation": {"overall_score": 0.0},
        }

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Conversation summary - now delegated to external conversation manager"""
        return {"total_queries": 0, "avg_confidence": 0.0, "recent_queries": []}


def run_interactive_chatbot():
    """Interaktif chatbot'u çalıştır"""
    chatbot = AdvancedRAGChatbot()

    print("\n🤖 Gelişmiş RAG Chatbot başlatıldı!")
    print("💡 Komutlar: 'exit' (çıkış), 'history' (geçmiş), 'help' (yardım)\n")

    while True:
        try:
            user_input = input("Kullanıcı: ").strip()

            if user_input.lower() in ["exit", "quit", "bye"]:
                summary = chatbot.get_conversation_summary()
                print(
                    f"\nBot: Görüşmek üzere! Toplam {summary['total_queries']} soru sordunuz."
                )
                print(f"Ortalama güven skoru: {summary['avg_confidence']:.2f}")
                break

            elif user_input.lower() == "history":
                summary = chatbot.get_conversation_summary()
                print(f"\n📊 Konuşma Özeti:")
                print(f"Toplam soru: {summary['total_queries']}")
                print(f"Ortalama güven: {summary['avg_confidence']:.2f}")
                if summary["recent_queries"]:
                    print("Son sorular:", summary["recent_queries"])
                continue

            elif user_input.lower() == "help":
                print("\n🔧 Yardım:")
                print("- Normal sorularınızı yazabilirsiniz")
                print("- 'history' komutu konuşma geçmişini gösterir")
                print("- 'exit' komutu chatbot'tan çıkar")
                print("- Daha kesin cevaplar için spesifik sorular sorun")
                continue

            if not user_input:
                continue

            # Process query
            result = chatbot.process_query(user_input)

            # Display response
            print(f"\nBot: {result['response']}")

            # Display quality info (opsiyonel)
            print(
                f"\n📊 Güven: {result['confidence']:.2f} | Kalite: {result['quality_level']}"
            )
            if result.get("sources"):
                print(f"📚 Kaynaklar: {', '.join(result['sources'][:3])}")

            print()  # Boş satır

        except KeyboardInterrupt:
            print("\nBot: Görüşmek üzere!")
            break
        except Exception as e:
            print(f"⚠️ Hata oluştu: {e}")
            continue


if __name__ == "__main__":
    run_interactive_chatbot()


def get_answer(question: str) -> str:
    """Basit API fonksiyonu - batch_ask.py için"""
    try:
        chatbot = AdvancedRAGChatbot()
        result = chatbot.process_query(question)
        
        # Kaynak bilgisini ekle
        response = result['response']
        if result.get('sources'):
            sources = ', '.join(result['sources'][:2])  # İlk 2 kaynağı al
            response += f"\n\nKullanılan kaynak: {sources}"
        
        return response
    except Exception as e:
        return f"Hata oluştu: {str(e)}"