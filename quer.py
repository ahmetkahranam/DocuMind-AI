import requests
import re
import json
from typing import Dict, Any, Optional, List
from config import config
import logging
import ollama

logger = logging.getLogger(__name__)


def temizle_yanit(yazi: str) -> str:
    """Yanıtı temizle ve düzenle"""
    if not yazi:
        return ""

    # <think> etiketlerini kaldır
    yazi = re.sub(r"<think>.*?</think>", "", yazi, flags=re.DOTALL | re.IGNORECASE)

    # HTML etiketlerini kaldır
    yazi = re.sub(r"<.*?>", "", yazi, flags=re.DOTALL)

    # Markdown işaretlerini temizle
    yazi = re.sub(r"\*\*|__|~~|`", "", yazi)

    # Eksik parantezleri temizle - satır sonunda tek parantez
    yazi = re.sub(r'\s*\($\s*', '', yazi, flags=re.MULTILINE)  # Satır sonunda tek açık parantez
    yazi = re.sub(r'\s*\)$\s*', '', yazi, flags=re.MULTILINE)  # Satır sonunda tek kapalı parantez
    yazi = re.sub(r'\s*\[\s*$', '', yazi, flags=re.MULTILINE)  # Satır sonunda tek açık köşeli parantez
    yazi = re.sub(r'\s*\]\s*$', '', yazi, flags=re.MULTILINE)  # Satır sonunda tek kapalı köşeli parantez
    
    # Eksik noktalama işaretlerini temizle
    yazi = re.sub(r'\s*[,;:]\s*$', '', yazi, flags=re.MULTILINE)  # Satır sonunda virgül, noktalı virgül, iki nokta

    # Çoklu boşlukları temizle
    yazi = re.sub(r"\s+", " ", yazi).strip()

    # Çok uzun yanıtları kısalt
    if len(yazi) > config.MAX_ANSWER_LENGTH:
        words = yazi.split()
        yazi = " ".join(words[: config.MAX_ANSWER_LENGTH // 5]) + "..."

    return yazi


def enhanced_prompt_engineering(prompt: str, query_category: str = "general") -> str:
    """Gelişmiş prompt mühendisliği"""

    # Kategori bazlı ek talimatlar
    category_instructions = {
        "procedure": "\nAdım adım açıklama yapın. Sıralı liste halinde sunun.",
        "temporal": "\nTarih ve zaman bilgilerini kesin olarak belirtin.",
        "quantitative": "\nSayısal bilgileri tam ve doğru verin.",
        "definition": "\nTanımları açık ve anlaşılır yapın.",
        "explanation": "\nSebep-sonuç ilişkilerini açıklayın.",
        "location": "\nYer bilgilerini spesifik belirtin.",
        "general": "\nKapsamlı ve düzenli açıklama yapın.",
    }

    enhanced_prompt = prompt + category_instructions.get(query_category, "")

    # Maksimum güçlü prompt talimatları
    quality_instructions = """

ÇÖZÜLMEZ PROMPT TALİMATLARI:
- Verilen belgelerdeki HER METİN PARÇASını tamamen tara ve oku
- Sayılı madde ve kuralları mutlaka bul ve belirt
- Anahtar kelimeleri dikkatli ara
- Madde numaralarını (örn: 14. madde) MUTLAKA belirt  
- Kesin ve doğrudan yanıt ver - "galiba, sanırım" YASAK
- SADECE gerçekten hiç bilgi yoksa "belirtilmemiş" de
- Belgede bilgi varsa "belirtilmemiş" deme - bu YANLIŞ
- Her belge parçasında detaylı arama yapman GEREKİYOR"""

    return enhanced_prompt + quality_instructions


def ask_local_llm(
    prompt: str,
    model: Optional[str] = None,
    query_category: str = "general",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Ollama yerel LLM kullanarak çağrı"""

    if model is None:
        model = config.LLM_MODEL
    if temperature is None:
        temperature = config.LLM_TEMPERATURE
    if max_tokens is None:
        max_tokens = config.LLM_MAX_TOKENS

    # Prompt'u geliştir
    enhanced_prompt = enhanced_prompt_engineering(prompt, query_category)

    try:
        logger.info(f"🔄 Ollama LLM çağrısı yapılıyor - Model: {model}")

        # Ollama API çağrısı
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": enhanced_prompt}],
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        )

        raw_yanit = response['message']['content']

        if not raw_yanit:
            logger.warning("⚠️ Ollama'dan boş yanıt alındı")
            return "⚠️ Modelden net bir yanıt alınamadı."

        # Yanıtı temizle
        temiz_yanit = temizle_yanit(raw_yanit)

        # Minimum uzunluk kontrolü
        if len(temiz_yanit) < config.MIN_ANSWER_LENGTH:
            logger.warning(f"⚠️ Çok kısa yanıt: {len(temiz_yanit)} karakter")
            return (
                "⚠️ Yeterince detaylı yanıt alınamadı. Lütfen daha spesifik soru sorun."
            )

        logger.info(f"✅ Ollama yanıtı alındı - {len(temiz_yanit)} karakter")
        return temiz_yanit

    except Exception as e:
        logger.error(f"⚠️ Ollama LLM hatası: {e}")
        if "not found" in str(e).lower() or "model" in str(e).lower():
            return f"⚠️ Model '{model}' bulunamadı. Lütfen 'ollama pull {model}' komutunu çalıştırın."
        elif "connection" in str(e).lower():
            return "⚠️ Ollama servisine bağlanılamadı. Lütfen 'ollama serve' komutunu çalıştırın."
        else:
            return f"⚠️ Yerel LLM hatası: {str(e)[:100]}"


def batch_llm_requests(
    prompts_list: List[Any], model: Optional[str] = None
) -> List[str]:
    """Çoklu LLM istekleri için batch işleme"""
    results = []

    for i, prompt_data in enumerate(prompts_list):
        if isinstance(prompt_data, dict):
            prompt = prompt_data.get("prompt", "")
            category = prompt_data.get("category", "general")
        else:
            prompt = str(prompt_data)
            category = "general"

        logger.info(f"🔄 Batch işlem {i+1}/{len(prompts_list)}")

        result = ask_local_llm(prompt, model=model, query_category=category)
        results.append(result)

    return results


def validate_llm_connection() -> Dict[str, Any]:
    """Ollama bağlantısını doğrula"""
    try:
        logger.info("🔄 Ollama bağlantısı test ediliyor...")

        # Mevcut modelleri al
        models_response = ollama.list()
        available_models = [model['name'] for model in models_response.get('models', [])]

        # Test çağrısı
        response = ollama.chat(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": "Test"}],
            options={"num_predict": 5}
        )

        target_model = config.LLM_MODEL
        model_available = any(target_model in model for model in available_models)

        return {
            "connected": True,
            "service": "Ollama Local LLM",
            "available_models": available_models,
            "target_model": target_model,
            "target_model_available": model_available,
            "total_models": len(available_models),
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "connection" in error_msg or "refused" in error_msg:
            return {
                "connected": False,
                "error": "Ollama servisine bağlanılamadı",
                "suggestion": "'ollama serve' komutunu çalıştırın",
            }
        elif "not found" in error_msg or "model" in error_msg:
            return {
                "connected": False,
                "error": f"Model '{config.LLM_MODEL}' bulunamadı",
                "suggestion": f"'ollama pull {config.LLM_MODEL}' komutunu çalıştırın",
            }
        else:
            return {
                "connected": False,
                "error": f"Ollama hatası: {str(e)[:100]}",
                "suggestion": "Ollama kurulumunu kontrol edin",
            }


def test_llm_quality() -> Dict[str, Any]:
    """LLM yanıt kalitesini test et"""
    test_prompts = [
        {
            "prompt": "Sistem hakkında kısa bilgi ver.",
            "category": "general",
            "expected_keywords": ["bilgi", "sistem", "doküman"],
        },
        {
            "prompt": "İşlem adımları nelerdir?",
            "category": "procedure",
            "expected_keywords": ["adım", "işlem", "prosedür"],
        },
    ]

    results = []

    for test in test_prompts:
        response = ask_local_llm(test["prompt"], query_category=test["category"])

        # Keyword kontrolü
        keyword_found = any(
            keyword in response.lower() for keyword in test["expected_keywords"]
        )

        results.append(
            {
                "prompt": test["prompt"],
                "response": response[:100] + "...",  # İlk 100 karakter
                "length": len(response),
                "keywords_found": keyword_found,
                "quality": "Good" if keyword_found and len(response) > 50 else "Poor",
            }
        )

    return {
        "tests": results,
        "passed": sum(1 for r in results if r["quality"] == "Good"),
        "total": len(results),
    }


if __name__ == "__main__":
    # Test işlemleri
    print("🧪 Ollama Bağlantı Testi...")
    connection_status = validate_llm_connection()
    print(f"Bağlantı durumu: {connection_status}")

    if connection_status.get("connected"):
        print("\n🧪 LLM Kalite Testi...")
        quality_results = test_llm_quality()
        print(f"Geçen testler: {quality_results['passed']}/{quality_results['total']}")

        for test in quality_results["tests"]:
            print(f"✅ {test['prompt'][:30]}... - Kalite: {test['quality']}")
    else:
        print("❌ Ollama bağlantısı kurulamadı, kalite testi yapılamıyor.")
        print(f"Hata: {connection_status.get('error', 'Bilinmeyen hata')}")
        print(
            f"Öneri: {connection_status.get('suggestion', 'Konfigürasyonu kontrol edin')}"
        )