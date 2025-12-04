from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import chromadb
from quer import ask_local_llm, temizle_yanit
from base import AdvancedDocumentProcessor
from embedder import LocalEmbedder
from chroma import ChromaDBManager
from pathlib import Path
from config import config
import re

import os
import datetime
from datetime import datetime as dt
import shutil
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)
CORS(app)  # React uygulamasından API çağrıları için

# Import config for consistency
from config import config

# Use config values for consistency
EMBEDDING_MODEL = config.EMBEDDING_MODEL

# Unikys entegrasyonunda kullanılacak ek importlar
import requests
UPLOAD_FOLDER = "uploads"
EMBEDDINGS_FOLDER = "embeddings"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EMBEDDINGS_FOLDER, exist_ok=True)

# Initialize enhanced components with consistent config
processor = AdvancedDocumentProcessor()
embedder = LocalEmbedder(model=config.EMBEDDING_MODEL)  # Local SentenceTransformer
chroma_manager = ChromaDBManager()


def allowed_file(filename):
    """Dosya uzantısının desteklenip desteklenmediğini kontrol eder"""
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_size(file):
    """Dosya boyutunu kontrol eder"""
    file.seek(0, 2)  # EOF'a git
    size = file.tell()
    file.seek(0)  # Başa dön
    return size


def generate_unique_filename(filename, upload_folder):
    """Dosya adı çakışması varsa benzersiz isim oluşturur"""
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename

    while os.path.exists(os.path.join(upload_folder, new_filename)):
        new_filename = f"{name}_{counter}{ext}"
        counter += 1

    return new_filename


def embed_query(text: str):
    """
    Soru için embedding hesaplar ve liste döner.
    Sadece LocalEmbedder (SentenceTransformer) kullanır.
    """
    embedding = embedder.embed_single(text)
    return embedding.tolist()


def initialize_database():
    from question_db import init_db

    try:
        init_db()
        print("Veritabanı başarıyla başlatıldı.")
    except Exception as e:
        print(f"Veritabanı başlatılamadı: {e}")


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_query = data.get("message", "").strip()
        user_id = data.get("user_id", "anonymous")

        if not user_query:
            return jsonify({"error": "Boş mesaj gönderildi"}), 400

        # Güncellenmiş RAG sistemi kullan
        from rag_chatbot import AdvancedRAGChatbot

        # RAG chatbot'u başlat
        if not hasattr(chat, "_chatbot"):
            chat._chatbot = AdvancedRAGChatbot()

        # Enhanced chat manager'dan sadece selamlama/veda kontrolü al
        from enhanced_chat_manager import conversation_manager

        # 1. Karma mesaj kontrolü (selamlama + soru)
        has_greeting = any(
            re.search(pattern, user_query.lower())
            for pattern in conversation_manager.greeting_patterns
        )
        has_question = any(
            indicator in user_query.lower()
            for indicator in [
                "nasıl",
                "ne",
                "nerede",
                "neden",
                "kim",
                "hangi",
                "kaç",
                "ne zaman",
                "nasıl",
                "nedir",
                "kural",
                "prosedür",
                "işlem",
                "gerekli",
                "şart",
                "başvuru",
                "belge",
                "form",
                "süreç",
                "?",
            ]
        )

        # 2. Sadece selamlama kontrolü
        if conversation_manager.is_greeting(user_query):
            greeting_response = conversation_manager.get_greeting_response()
            conversation_manager.add_to_conversation(
                user_id, user_query, greeting_response
            )
            # Selamlama için soru kaydı yapmıyoruz (soru sayısına dahil edilmez)
            return jsonify(
                {
                    "response": greeting_response,
                    "sources": [],
                    "type": "greeting",
                    "confidence": 1.0,
                    "quality_level": "Otomatik Yanıt",
                }
            )

        # 3. Veda kontrolü
        if conversation_manager.is_goodbye(user_query):
            goodbye_response = conversation_manager.get_goodbye_response()
            conversation_manager.add_to_conversation(
                user_id, user_query, goodbye_response
            )
            # Veda için soru kaydı yapmıyoruz (soru sayısına dahil edilmez)
            return jsonify(
                {
                    "response": goodbye_response,
                    "sources": [],
                    "type": "goodbye",
                    "confidence": 1.0,
                    "quality_level": "Otomatik Yanıt",
                }
            )

        # 4. Güncellenmiş RAG sistemi ile yanıt al
        rag_result = chat._chatbot.process_query(user_query)

        # Karma mesaj için "Merhaba!" ile başla
        final_response = rag_result["response"]
        if has_greeting and has_question:
            final_response = "Merhaba! " + rag_result["response"]

        # Soru ve yanıtı veritabanına kaydet
        try:
            from question_db import add_question, init_db

            init_db()  # Veritabanını başlat

            # Kaynak bilgisini al - sadece başarılı cevaplar için
            source_file = None
            if rag_result.get("sources") and len(rag_result["sources"]) > 0:
                # Confidence düşükse veya quality level "Bilgi Yok", "Düşük Güven", "Hata" ise kaynak kaydetme
                confidence = rag_result.get("confidence", 0)
                quality_level = rag_result.get("quality_level", "")

                # Başarılı cevaplar için kaynak kaydet
                success_conditions = (
                    confidence > 0.3
                    and quality_level not in ["Bilgi Yok", "Düşük Güven", "Hata"]
                    and not any(
                        phrase in final_response.lower()
                        for phrase in [
                            "kesin bilgi bulunamadı",
                            "spesifik bir soru sormayı deneyebilirsiniz",
                            "sorunuzu işlerken bir hata oluştu",
                            "bu konuda yeterli bilgi bulunamadı",
                        ]
                    )
                )

                if success_conditions:
                    source_file = rag_result["sources"][0]

            # Soruyu veritabanına kaydet

            print(f"[DEBUG] add_question çağrısı: source_file={source_file}")
            qid = add_question(
                question=user_query,
                answer=final_response,
                source_file=source_file,
                source_keyword=None,  # Gerekirse eklenebilir
                topic=None,  # Otomatik tespit edilecek
            )
            print(f"[DEBUG] add_question sonrası: qid={qid}, source_file={source_file}")
            # Kaynak dosya varsa question_sources tablosuna da ekle
            if source_file:
                from question_db import add_question_source
                add_question_source(qid, source_file)
                print(f"[DEBUG] add_question_source çağrıldı: qid={qid}, source_file={source_file}")

            # Stats.json dosyasını güncelle
            update_stats_json()

        except Exception as e:
            print(f"Soru kaydedilirken hata: {e}")

        # Conversation manager'a ekle
        conversation_manager.add_to_conversation(user_id, user_query, final_response)

        # API response format'ına uygun döndür
        return jsonify(
            {
                "response": final_response,
                "sources": rag_result.get("sources", []),  # Kaynakları sadece cevap balonunun altında göster
                "type": (
                    "mixed_response"
                    if (has_greeting and has_question)
                    else "rag_response"
                ),
                "confidence": rag_result.get("confidence", 0.5),
                "quality_level": rag_result.get("quality_level", "Normal"),
                "query_analysis": rag_result.get("query_analysis", {}),
                "retrieval_info": rag_result.get("retrieval_info", {}),
            }
        )

    except Exception as e:
        error_msg = f"Chat hatası: {str(e)}"
        print(error_msg)  # Hata mesajını logla
        return jsonify({"error": error_msg}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "OK", "message": "RAG Chatbot API çalışıyor"})


@app.route("/api/conversation/history", methods=["GET"])
def get_conversation_history():
    """Kullanıcının sohbet geçmişini getir"""
    try:
        user_id = request.args.get("user_id", "anonymous")
        from enhanced_chat_manager import conversation_manager

        history = conversation_manager.get_conversation_history(user_id)
        return jsonify(
            {
                "user_id": user_id,
                "conversation_history": history,
                "total_messages": len(history),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/conversation/clear", methods=["POST"])
def clear_conversation():
    """Kullanıcının sohbet geçmişini temizle ve chatbot'u sıfırla"""
    try:
        data = request.get_json()
        user_id = data.get("user_id", "anonymous")
        from enhanced_chat_manager import conversation_manager

        # Enhanced chat manager'daki conversation'ı temizle
        if user_id in conversation_manager.conversations:
            del conversation_manager.conversations[user_id]

        # Chatbot instance'ını da sıfırla (yeni sohbet için temiz başlangıç)
        if hasattr(chat, "_chatbot"):
            delattr(chat, "_chatbot")

        return jsonify(
            {
                "message": "Sohbet geçmişi temizlendi ve chatbot sıfırlandı",
                "user_id": user_id,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


# Admin panel backend endpoints
@app.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    """Dosya yükleme endpoint'i - geliştirilmiş versiyon"""
    try:
        files = request.files.getlist("files")
        if not files or not any(f.filename for f in files):
            return jsonify({"error": "Dosya seçilmedi"}), 400

        uploaded = []
        errors = []

        for f in files:
            fname = f.filename
            if not fname:
                continue

            # Dosya uzantısı kontrolü
            if not allowed_file(fname):
                errors.append(f"{fname}: Desteklenmeyen dosya formatı")
                continue

            # Dosya boyutu kontrolü
            file_size = get_file_size(f)
            if file_size > MAX_FILE_SIZE:
                errors.append(
                    f"{fname}: Dosya boyutu çok büyük (max {MAX_FILE_SIZE // (1024*1024)}MB)"
                )
                continue

            # Güvenli dosya adı oluştur
            filename = secure_filename(fname)
            if not filename:
                errors.append(f"{fname}: Geçersiz dosya adı")
                continue

            # Benzersiz dosya adı oluştur
            unique_filename = generate_unique_filename(filename, UPLOAD_FOLDER)
            save_path = os.path.join(UPLOAD_FOLDER, unique_filename)

            try:
                f.save(save_path)
                uploaded.append(
                    {
                        "original_name": fname,
                        "saved_name": unique_filename,
                        "size": file_size,
                        "path": save_path,
                    }
                )
            except Exception as e:
                errors.append(f"{fname}: Kaydetme hatası - {str(e)}")

        response = {"uploaded": uploaded}
        if errors:
            response["errors"] = errors

        status_code = 201 if uploaded else 400
        return jsonify(response), status_code

    except Exception as e:
        return jsonify({"error": f"Yükleme hatası: {str(e)}"}), 500


@app.route("/api/admin/documents", methods=["GET"])
def admin_list_documents():
    """Yüklenen dokümanları listeler - geliştirilmiş versiyon"""
    try:
        docs = []

        # Enhanced JSON dosyalarından keyword bilgilerini yükle
        keyword_data = {}
        for enhanced_file in [
            "enhanced_document_data.json",
            "enhanced_document_data_with_embeddings.json",
        ]:
            if os.path.exists(enhanced_file):
                try:
                    with open(enhanced_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for item in data:
                            if "filename" in item and "keyword" in item:
                                keyword_data[item["filename"]] = item["keyword"]
                except Exception as e:
                    print(f"Enhanced dosya okunamadı {enhanced_file}: {e}")

        # uploads ve docs klasörlerinde fiziksel olarak var olan dosyaları kesin olarak listele
        # Sadece docs klasöründeki dosyaları listele
        docs_folder = os.path.join(os.getcwd(), "docs")
        if os.path.exists(docs_folder):
            for filename in os.listdir(docs_folder):
                if allowed_file(filename):
                    path = os.path.join(docs_folder, filename)
                    if not os.path.isfile(path):
                        continue
                    try:
                        stat = os.stat(path)
                        mtime = datetime.datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat()
                        size = stat.st_size
                        status = check_document_status(filename)
                        keyword = keyword_data.get(filename, None)
                        docs.append(
                            {
                                "filename": filename,
                                "date": mtime,
                                "size": size,
                                "size_mb": round(size / (1024 * 1024), 2),
                                "status": status,
                                "extension": (
                                    filename.rsplit(".", 1)[1].lower()
                                    if "." in filename
                                    else ""
                                ),
                                "folder": os.path.basename(docs_folder),
                                "keyword": keyword,
                            }
                        )
                    except OSError as e:
                        print(f"Dosya bilgisi alınamadı {filename}: {e}")
                        continue
        # Tarihe göre sırala (en yeni ilk)
        docs.sort(key=lambda x: x["date"], reverse=True)
        return jsonify({"documents": docs, "total": len(docs)})

    except Exception as e:
        return jsonify({"error": f"Dosya listesi alınamadı: {str(e)}"}), 500


def check_document_status(filename):
    """Dokümanın ChromaDB'de işlenip işlenmediğini kontrol eder"""
    try:
        # ChromaDB'de dosya adına göre ara
        collection_info = chroma_manager.get_collection_info()
        unique_sources = collection_info.get("unique_sources", [])

        if filename in unique_sources:
            return "processed"
        else:
            return "pending"

    except Exception as e:
        return "unknown"


@app.route("/api/admin/process", methods=["POST"])
def admin_process_documents():
    """Dokümanları işler - geliştirilmiş versiyon"""
    try:
        # Belirli dosyaları işlemek için filename parametresi
        request_data = request.get_json() or {}
        target_files = request_data.get("files", [])  # Boş liste = tüm dosyalar

        # Mevcut dosyaları kontrol et
        if not os.path.exists(UPLOAD_FOLDER) or not os.listdir(UPLOAD_FOLDER):
            return jsonify({"error": "İşlenecek dosya bulunamadı"}), 400

        # Hedef dosyaları filtrele
        if target_files:
            # Belirli dosyaları işle
            files_to_process = []
            for filename in target_files:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.exists(file_path) and processor.SUPPORTED_FORMATS.get(
                    Path(file_path).suffix.lower()
                ):
                    files_to_process.append(file_path)

            if not files_to_process:
                return jsonify({"error": "Geçerli dosya bulunamadı"}), 400

        else:
            # Tüm dosyaları işle
            files_to_process = [
                os.path.join(UPLOAD_FOLDER, f)
                for f in os.listdir(UPLOAD_FOLDER)
                if processor.SUPPORTED_FORMATS.get(Path(f).suffix.lower())
            ]

        processed_files = []
        failed_files = []

        # Her dosya için işleme
        for file_path in files_to_process:
            try:
                # Doküman tipine göre metin çıkartma
                file_ext = Path(file_path).suffix.lower()

                if file_ext == ".pdf":
                    text, metadata = processor.extract_text_from_pdf(file_path)
                elif file_ext in [".docx", ".doc"]:
                    text, metadata = processor.extract_text_from_docx(file_path)
                else:
                    text, metadata = processor.extract_text_universal(file_path)

                if not text.strip():
                    failed_files.append(f"{metadata.filename}: Metin çıkarılamadı")
                    continue

                # Metni temizle ve chunk'lara böl
                cleaned_text = processor.advanced_clean_text(text)
                processed_chunks = processor.adaptive_chunk_creation(
                    cleaned_text, metadata
                )

                if not processed_chunks:
                    failed_files.append(f"{metadata.filename}: Chunk oluşturulamadı")
                    continue

                # Chunk'lar için embedding oluştur
                chunk_texts = [chunk.content for chunk in processed_chunks]
                embeddings = embedder.embed_batch(chunk_texts)

                # ChromaDB'ye eklemek için veri formatı
                documents_batch = [
                    {
                        "filename": metadata.filename,
                        "file_type": metadata.file_type,
                        "file_size": metadata.file_size,
                        "content": cleaned_text,
                        "chunks": chunk_texts,
                        "embeddings": [emb.tolist() for emb in embeddings],
                        "chunk_metadata": [
                            chunk.metadata or {} for chunk in processed_chunks
                        ],
                        "chunk_count": len(chunk_texts),
                        "character_count": len(cleaned_text),
                        "document_metadata": {
                            "creation_date": metadata.creation_date,
                            "modification_date": metadata.modification_date,
                            "author": metadata.author,
                            "title": metadata.title,
                            "page_count": metadata.page_count,
                            "checksum": metadata.checksum,
                        },
                    }
                ]

                # ChromaDB'ye ekle
                result = chroma_manager.add_documents_batch(documents_batch)

                if result.get("total_added", 0) > 0:
                    processed_files.append(metadata.filename)
                    
                    # Enhanced JSON dosyalarına ekle (pipeline mantığı)
                    try:
                        # enhanced_document_data.json'a ekle
                        enhanced_data_path = "enhanced_document_data.json"
                        if os.path.exists(enhanced_data_path):
                            with open(enhanced_data_path, "r", encoding="utf-8") as f:
                                enhanced_data = json.load(f)
                        else:
                            enhanced_data = []
                        
                        enhanced_data.extend(documents_batch)
                        
                        with open(enhanced_data_path, "w", encoding="utf-8") as f:
                            json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
                        
                        # enhanced_document_data_with_embeddings.json'a ekle
                        enhanced_embeddings_path = "enhanced_document_data_with_embeddings.json"
                        if os.path.exists(enhanced_embeddings_path):
                            with open(enhanced_embeddings_path, "r", encoding="utf-8") as f:
                                enhanced_embeddings_data = json.load(f)
                        else:
                            enhanced_embeddings_data = []
                        
                        enhanced_embeddings_data.extend(documents_batch)
                        
                        with open(enhanced_embeddings_path, "w", encoding="utf-8") as f:
                            json.dump(enhanced_embeddings_data, f, ensure_ascii=False, indent=2)
                            
                        print(f"[PIPELINE] {metadata.filename} enhanced JSON dosyalarına eklendi")
                        
                    except Exception as e:
                        print(f"[PIPELINE] Enhanced JSON ekleme hatası {metadata.filename}: {str(e)}")
                        
                else:
                    failed_files.append(f"{metadata.filename}: ChromaDB ekleme hatası")

            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")

        response = {"processed": processed_files}
        if failed_files:
            response["failures"] = failed_files

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"İşleme hatası: {str(e)}"}), 500


@app.route("/api/admin/document/<filename>", methods=["DELETE"])
def admin_delete_document(filename):
    """Dosya silme - geliştirilmiş versiyon"""
    try:
        # Güvenlik kontrolü
        if not filename or ".." in filename or "/" in filename:
            return jsonify({"error": "Geçersiz dosya adı"}), 400


        # Hem uploads hem docs klasöründen sil
        deleted_any = False
        for folder in [UPLOAD_FOLDER, os.path.join(os.getcwd(), "docs")]:
            path = os.path.join(folder, filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted_any = True
                except Exception as e:
                    print(f"{folder} klasöründen silinemedi: {e}")

        # Tüm ilgili JSON dosyalarından kaldır
        def remove_from_json_file(json_path):
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Sadece bu dosya ile ilgili verileri kaldır
                    original_count = len(data)
                    new_data = [item for item in data if item.get("filename") != filename]
                    
                    if len(new_data) != original_count:
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(new_data, f, ensure_ascii=False, indent=2)
                        removed_count = original_count - len(new_data)
                        print(f"{json_path} dosyasından {filename} ile ilgili {removed_count} kayıt kaldırıldı")
                    else:
                        print(f"{json_path} dosyasında {filename} için kayıt bulunamadı")
                except Exception as e:
                    print(f"{json_path} dosyasından silme hatası: {e}")

        for json_file in [
            "enhanced_document_data.json",
            "enhanced_document_data_with_embeddings.json",
            "uploads_base.json",
            "uploads_with_embed.json",
            os.path.join(EMBEDDINGS_FOLDER, "embeddings_data.json")
        ]:
            remove_from_json_file(json_file)

        # ChromaDB'den de kaldır (varsa)
        try:
            remove_from_chromadb(filename)
        except Exception as e:
            print(f"ChromaDB'den kaldırma hatası: {e}")

        # Soru veritabanından da kaldır
        try:
            from question_db import delete_questions_by_source_file
            delete_questions_by_source_file(filename)
        except Exception as e:
            print(f"question_db'den silme hatası: {e}")

        if deleted_any:
            return jsonify({"deleted": filename, "message": "Dosya ve tüm ilişkili veriler başarıyla silindi"})
        else:
            return jsonify({"deleted": filename, "message": "Dosya sistemde fiziksel olarak bulunamadı, ilişkili veriler temizlendi"})

    except Exception as e:
        return jsonify({"error": f"Silme hatası: {str(e)}"}), 500



# ChromaDB silme fonksiyonu artık chroma_utils.py'den import edilecek
from chroma_utils import remove_from_chromadb


def remove_from_embeddings_json(filename):
    """Dosyayı embeddings sisteminden kaldırır"""
    try:
        # Önce ChromaDB'den kaldır
        remove_from_chromadb(filename)

        # Eski JSON tabanlı sistem için backup temizlik
        json_file = os.path.join(EMBEDDINGS_FOLDER, "embeddings_data.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Dosyayı filtrele
                updated_data = [
                    item for item in data if item.get("filename") != filename
                ]

                if len(updated_data) != len(data):
                    # Değişiklik varsa kaydet
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(updated_data, f, ensure_ascii=False, indent=2)
                    print(f"JSON'dan {filename} kaldırıldı")

            except Exception as e:
                print(f"JSON temizleme hatası: {e}")

        # Metadata güncelle
        update_embeddings_metadata()

    except Exception as e:
        print(f"Embeddings sisteminden kaldırma hatası: {e}")


# Update document endpoint
@app.route("/api/admin/document/<filename>", methods=["PUT"])
def admin_update_document(filename):
    """Dosya güncelleme - geliştirilmiş versiyon"""
    try:
        # Güvenlik kontrolü
        if not filename or ".." in filename or "/" in filename:
            return jsonify({"error": "Geçersiz dosya adı"}), 400

        if not allowed_file(filename):
            return jsonify({"error": "Desteklenmeyen dosya formatı"}), 400

        if "file" not in request.files:
            return jsonify({"error": "Dosya gönderilmedi"}), 400

        file = request.files["file"]
        fname = file.filename

        if not file or not fname:
            return jsonify({"error": "Geçersiz dosya"}), 400

        # Dosya uzantısı kontrolü
        old_ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        new_ext = fname.rsplit(".", 1)[1].lower() if "." in fname else ""

        if old_ext != new_ext:
            return jsonify({"error": "Dosya uzantısı uyumsuz"}), 400

        # Dosya boyutu kontrolü
        file_size = get_file_size(file)
        if file_size > MAX_FILE_SIZE:
            return (
                jsonify(
                    {
                        "error": f"Dosya boyutu çok büyük (max {MAX_FILE_SIZE // (1024*1024)}MB)"
                    }
                ),
                400,
            )

        save_path = os.path.join(UPLOAD_FOLDER, filename)

        if not os.path.exists(save_path):
            return jsonify({"error": "Güncellenecek dosya bulunamadı"}), 404

        # Eski dosyayı yedekle (isteğe bağlı)
        backup_path = f"{save_path}.backup"
        try:
            import shutil

            shutil.copy2(save_path, backup_path)

            # Yeni dosyayı kaydet
            file.save(save_path)

            # Yedek dosyayı sil
            os.remove(backup_path)

            # JSON ve ChromaDB'den eski verileri temizle
            try:
                remove_from_embeddings_json(filename)
                remove_from_chromadb(filename)
            except Exception as e:
                print(f"Eski veri temizleme hatası: {e}")

            return jsonify(
                {
                    "updated": filename,
                    "size": file_size,
                    "message": "Dosya başarıyla güncellendi. Yeniden işlenmesi gerekiyor.",
                }
            )

        except Exception as e:
            # Hata durumunda yedekten geri yükle
            if os.path.exists(backup_path):
                import shutil

                shutil.copy2(backup_path, save_path)
                os.remove(backup_path)
            raise e

    except Exception as e:
        return jsonify({"error": f"Güncelleme hatası: {str(e)}"}), 500


# Yeni dinamik endpoint'ler
@app.route("/api/admin/documents/bulk", methods=["DELETE"])
def admin_bulk_delete():
    """Toplu dosya silme ve pipeline reset"""
    try:
        data = request.get_json()
        filenames = data.get("files", [])

        if not filenames:
            return jsonify({"error": "Silinecek dosya belirtilmedi"}), 400

        deleted = []
        errors = []

        import subprocess
        import sys

        python_exe = sys.executable

        # Silme işleminden önce kalan dosyaların anahtar kelime bilgilerini kaydet
        keyword_backup = {}
        try:
            with open("enhanced_document_data.json", "r", encoding="utf-8") as f:
                current_data = json.load(f)
                for item in current_data:
                    filename = item.get("filename")
                    if filename and filename not in filenames and "keyword" in item:
                        keyword_backup[filename] = item["keyword"]
        except Exception as e:
            errors.append(f"Anahtar kelime backup hatası: {str(e)}")


        # 1. Sadece seçili dosyaların ChromaDB'den chunk'larını sil
        for filename in filenames:
            try:
                remove_from_chromadb(filename)
            except Exception as e:
                errors.append(f"ChromaDB silme hatası ({filename}): {str(e)}")

        # 2. Enhanced json dosyalarından sadece seçili dosyaları kaldır
        for enhanced_file in [
            "enhanced_document_data.json",
            "enhanced_document_data_with_embeddings.json",
        ]:
            try:
                if os.path.exists(enhanced_file):
                    with open(enhanced_file, "r", encoding="utf-8") as f:
                        current_data = json.load(f)
                    
                    # Silinecek dosyaları filtrele
                    filtered_data = [
                        item for item in current_data 
                        if item.get("filename") not in filenames
                    ]
                    
                    with open(enhanced_file, "w", encoding="utf-8") as f:
                        json.dump(filtered_data, f, ensure_ascii=False, indent=2)
                        
                    print(f"[DELETE] {enhanced_file} dosyasından {len(current_data) - len(filtered_data)} kayıt kaldırıldı")
                else:
                    # Dosya yoksa boş liste oluştur
                    with open(enhanced_file, "w", encoding="utf-8") as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                        
            except Exception as e:
                errors.append(f"{enhanced_file} güncelleme hatası: {str(e)}")

        # 3. Seçili dosyaları docs klasöründen sil
        docs_folder = os.path.join(os.getcwd(), "docs")
        for filename in filenames:
            try:
                if not filename or ".." in filename or "/" in filename:
                    errors.append(f"{filename}: Geçersiz dosya adı")
                    continue
                path = os.path.join(docs_folder, filename)
                if os.path.exists(path):
                    os.remove(path)
                    deleted.append(filename)
                else:
                    errors.append(f"{filename}: Dosya bulunamadı (docs)")
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")

        # Silme işlemi tamamlandı - artık enhanced JSON'lar manuel olarak güncellendi
        response = {"deleted": deleted}
        if errors:
            response["errors"] = errors

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Toplu silme hatası: {str(e)}"}), 500


def remove_from_chromadb(filename):
    """ChromaDB'den belirli dosyaya ait chunk'ları siler"""
    try:
        from chroma_utils import remove_from_chromadb as real_remove_from_chromadb
        real_remove_from_chromadb(filename)
        print(f"[DELETE] ChromaDB'den {filename} kaldırıldı")
    except Exception as e:
        print(f"[DELETE] ChromaDB silme hatası {filename}: {str(e)}")
        raise


@app.route("/api/admin/documents/status", methods=["GET"])
def admin_documents_status():
    """Doküman işleme durumu özeti"""
    try:
        total_files = 0
        processed_files = 0
        pending_files = 0
        total_size = 0

        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                if allowed_file(filename):
                    total_files += 1
                    path = os.path.join(UPLOAD_FOLDER, filename)
                    total_size += os.path.getsize(path)

                    status = check_document_status(filename)
                    if status == "processed":
                        processed_files += 1
                    else:
                        pending_files += 1

        return jsonify(
            {
                "total_files": total_files,
                "processed_files": processed_files,
                "pending_files": pending_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "allowed_extensions": list(ALLOWED_EXTENSIONS),
                "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            }
        )

    except Exception as e:
        return jsonify({"error": f"Durum bilgisi alınamadı: {str(e)}"}), 500


@app.route("/api/admin/documents/search", methods=["GET"])
def admin_search_documents():
    """Doküman arama"""
    try:
        query = request.args.get("q", "").strip()
        file_type = request.args.get("type", "").strip()
        status = request.args.get("status", "").strip()

        docs = []
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                if not allowed_file(filename):
                    continue

                # Dosya adı filtresi
                if query and query.lower() not in filename.lower():
                    continue

                # Dosya tipi filtresi
                if file_type and not filename.lower().endswith(f".{file_type.lower()}"):
                    continue

                path = os.path.join(UPLOAD_FOLDER, filename)
                stat = os.stat(path)
                doc_status = check_document_status(filename)

                # Durum filtresi
                if status and status != doc_status:
                    continue

                docs.append(
                    {
                        "filename": filename,
                        "date": datetime.datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "size": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "status": doc_status,
                        "extension": (
                            filename.rsplit(".", 1)[1].lower()
                            if "." in filename
                            else ""
                        ),
                    }
                )

        # Tarihe göre sırala
        docs.sort(key=lambda x: x["date"], reverse=True)

        return jsonify(
            {
                "documents": docs,
                "total": len(docs),
                "query": query,
                "filters": {"type": file_type, "status": status},
            }
        )

    except Exception as e:
        return jsonify({"error": f"Arama hatası: {str(e)}"}), 500


@app.route("/api/admin/cleanup", methods=["POST"])
def admin_cleanup():
    """Sistem temizleme - işlenmemiş dosyaları ve eski verileri temizler"""
    try:
        data = request.get_json() or {}
        cleanup_type = data.get("type", "all")  # "unprocessed", "processed", "all"

        cleaned = []
        errors = []

        if cleanup_type in ["unprocessed", "all"]:
            # İşlenmemiş dosyaları temizle
            if os.path.exists(UPLOAD_FOLDER):
                for filename in os.listdir(UPLOAD_FOLDER):
                    if (
                        allowed_file(filename)
                        and check_document_status(filename) == "pending"
                    ):
                        try:
                            path = os.path.join(UPLOAD_FOLDER, filename)
                            os.remove(path)
                            cleaned.append(f"Unprocessed: {filename}")
                        except Exception as e:
                            errors.append(f"{filename}: {str(e)}")

        if cleanup_type in ["processed", "all"]:
            # Orphaned data temizle - sadece ChromaDB'de olan ama dosyası olmayan
            try:
                collection_info = chroma_manager.get_collection_info()
                unique_sources = collection_info.get("unique_sources", [])

                orphaned_sources = []
                for source in unique_sources:
                    if not os.path.exists(os.path.join(UPLOAD_FOLDER, source)):
                        orphaned_sources.append(source)

                # Orphaned sources için cleanup
                for source in orphaned_sources:
                    try:
                        remove_from_chromadb(source)
                        cleaned.append(f"Orphaned data: {source}")
                    except Exception as e:
                        errors.append(f"Orphaned cleanup {source}: {str(e)}")

            except Exception as e:
                errors.append(f"ChromaDB cleanup error: {str(e)}")

        # Metadata güncelle
        update_embeddings_metadata()

        return jsonify(
            {"cleaned": cleaned, "errors": errors, "cleanup_type": cleanup_type}
        )

    except Exception as e:
        return jsonify({"error": f"Temizleme hatası: {str(e)}"}), 500


def create_embeddings_metadata(processed_files):
    """Embedding işlemi sonrası metadata dosyası oluşturur"""
    try:
        # ChromaDB stats al
        stats = chroma_manager.get_stats()

        metadata = {
            "created_at": datetime.datetime.now().isoformat(),
            "total_processed": len(processed_files),
            "processed_files": processed_files,
            "embedding_model": EMBEDDING_MODEL,
            "chromadb_stats": stats,
            "folder_structure": {
                "chroma_db": chroma_manager.chroma_path,
                "collection_name": chroma_manager.collection_name,
                "upload_folder": UPLOAD_FOLDER,
                "embeddings_folder": EMBEDDINGS_FOLDER,
            },
        }

        metadata_file = os.path.join(EMBEDDINGS_FOLDER, "metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Metadata oluşturma hatası: {e}")


def update_embeddings_metadata():
    """Embedding metadata'sını günceller"""
    try:
        # ChromaDB collection info al
        collection_info = chroma_manager.get_collection_info()

        metadata = {
            "updated_at": datetime.datetime.now().isoformat(),
            "total_chunks": collection_info.get("total_chunks", 0),
            "unique_sources": collection_info.get("source_count", 0),
            "file_types": collection_info.get("file_types", []),
            "embedding_model": EMBEDDING_MODEL,
            "chromadb_stats": chroma_manager.get_stats(),
            "folder_structure": {
                "chroma_db": chroma_manager.chroma_path,
                "collection_name": chroma_manager.collection_name,
                "upload_folder": UPLOAD_FOLDER,
                "embeddings_folder": EMBEDDINGS_FOLDER,
            },
        }

        metadata_file = os.path.join(EMBEDDINGS_FOLDER, "metadata.json")

        # Eski metadata varsa oluşturma tarihini koru
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    old_metadata = json.load(f)
                    if "created_at" in old_metadata:
                        metadata["created_at"] = old_metadata["created_at"]
            except:
                pass

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Metadata güncelleme hatası: {e}")


def get_embeddings_info():
    """Embedding sistemi hakkında bilgi döner"""
    try:
        # ChromaDB bilgileri
        collection_info = chroma_manager.get_collection_info()
        stats = chroma_manager.get_stats()

        info = {
            "embeddings_folder": EMBEDDINGS_FOLDER,
            "exists": os.path.exists(EMBEDDINGS_FOLDER),
            "chroma_db": {
                "path": chroma_manager.chroma_path,
                "collection_name": chroma_manager.collection_name,
                "total_chunks": collection_info.get("total_chunks", 0),
                "unique_sources": collection_info.get("source_count", 0),
                "file_types": collection_info.get("file_types", []),
                "index_size_mb": stats.get("index_size_mb", 0),
            },
            "files": [],
        }

        # Embeddings folder dosyaları
        if os.path.exists(EMBEDDINGS_FOLDER):
            for filename in os.listdir(EMBEDDINGS_FOLDER):
                file_path = os.path.join(EMBEDDINGS_FOLDER, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    info["files"].append(
                        {
                            "name": filename,
                            "size": stat.st_size,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "modified": datetime.datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                        }
                    )

        return info
    except Exception as e:
        return {"error": str(e)}


@app.route("/api/admin/embeddings/info", methods=["GET"])
def admin_embeddings_info():
    """Embedding dizini hakkında bilgi döner"""
    try:
        info = get_embeddings_info()

        # Metadata dosyasını da ekle
        metadata_file = os.path.join(EMBEDDINGS_FOLDER, "metadata.json")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    info["metadata"] = json.load(f)
            except Exception as e:
                info["metadata_error"] = str(e)

        return jsonify(info)

    except Exception as e:
        return jsonify({"error": f"Embedding bilgisi alınamadı: {str(e)}"}), 500


@app.route("/api/admin/embeddings/download", methods=["GET"])
def admin_download_embeddings():
    """Embedding dosyalarını indirme endpoint'i"""
    try:
        file_type = request.args.get(
            "type", "collection"
        )  # "collection", "metadata", "stats"

        if file_type == "collection":
            # ChromaDB collection'ı export et
            export_file = os.path.join(EMBEDDINGS_FOLDER, "collection_export.json")
            result = chroma_manager.export_data(export_file, include_embeddings=False)

            if result.get("error"):
                return jsonify({"error": result["error"]}), 500

            return send_file(
                export_file,
                as_attachment=True,
                download_name="chromadb_collection.json",
            )

        elif file_type == "metadata":
            metadata_file = os.path.join(EMBEDDINGS_FOLDER, "metadata.json")
            if os.path.exists(metadata_file):
                return send_file(
                    metadata_file, as_attachment=True, download_name="metadata.json"
                )
            else:
                return jsonify({"error": "Metadata bulunamadı"}), 404

        elif file_type == "stats":
            # İstatistik dosyası oluştur
            stats_file = os.path.join(EMBEDDINGS_FOLDER, "stats.json")
            stats = {
                "chromadb_stats": chroma_manager.get_stats(),
                "collection_info": chroma_manager.get_collection_info(),
                "embedder_info": embedder.get_model_info(),
                "generated_at": datetime.datetime.now().isoformat(),
            }

            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)

            return send_file(
                stats_file, as_attachment=True, download_name="embedding_stats.json"
            )
        else:
            return jsonify({"error": "Geçersiz dosya tipi"}), 400

    except Exception as e:
        return jsonify({"error": f"İndirme hatası: {str(e)}"}), 500


@app.route("/api/download/<path:filename>", methods=["GET"])
def download_file(filename):
    """Docs klasöründeki dosyaları indirme endpoint'i"""
    try:
        # Güvenlik kontrolü - directory traversal saldırısını engelle
        if not filename or ".." in filename:
            return jsonify({"error": "Geçersiz dosya adı"}), 400

        # Dosya adını güvenli hale getir
        safe_filename = secure_filename(filename)
        if not safe_filename:
            return jsonify({"error": "Geçersiz dosya adı"}), 400

        # Dosya yolunu oluştur
        docs_folder = os.path.join(os.getcwd(), "docs")
        file_path = os.path.join(docs_folder, safe_filename)

        # Dosyanın docs klasöründe olduğunu ve var olduğunu kontrol et
        if not os.path.exists(file_path):
            return jsonify({"error": f"Dosya bulunamadı: {safe_filename}"}), 404

        # Dosyanın gerçekten docs klasörü altında olduğunu kontrol et
        try:
            docs_folder_abs = os.path.abspath(docs_folder)
            file_path_abs = os.path.abspath(file_path)

            # Windows path normalization
            docs_folder_norm = os.path.normpath(docs_folder_abs).lower()
            file_path_norm = os.path.normpath(file_path_abs).lower()

            if not file_path_norm.startswith(docs_folder_norm):
                return jsonify({"error": "Dosya erişimi reddedildi"}), 403
        except Exception as path_error:
            return (
                jsonify({"error": f"Dosya yolu kontrolü hatası: {str(path_error)}"}),
                500,
            )

        # Dosya türü kontrolü
        allowed_extensions = {".pdf", ".docx", ".txt", ".md", ".doc"}
        file_ext = os.path.splitext(safe_filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({"error": "Dosya türü desteklenmiyor"}), 400

        # Dosyayı indir
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype="application/octet-stream",
        )

    except Exception as e:
        return jsonify({"error": f"İndirme hatası: {str(e)}"}), 500


@app.route("/api/admin/docs/list", methods=["GET"])
def list_downloadable_docs():
    """İndirilebilir dosyaları listele"""
    try:
        docs_folder = os.path.join(os.getcwd(), "docs")

        if not os.path.exists(docs_folder):
            return jsonify({"error": "Docs klasörü bulunamadı"}), 404

        files = []
        allowed_extensions = {".pdf", ".docx", ".txt", ".md", ".doc"}

        for filename in os.listdir(docs_folder):
            file_path = os.path.join(docs_folder, filename)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in allowed_extensions:
                    stat_info = os.stat(file_path)
                    files.append(
                        {
                            "filename": filename,
                            "size": stat_info.st_size,
                            "size_mb": round(stat_info.st_size / (1024 * 1024), 2),
                            "download_url": f"/api/download/{filename}",
                            "extension": file_ext,
                            "modified": stat_info.st_mtime,
                        }
                    )

        files.sort(key=lambda x: x["modified"], reverse=True)

        return jsonify(
            {"files": files, "total": len(files), "docs_folder": docs_folder}
        )

    except Exception as e:
        return jsonify({"error": f"Dosya listesi hatası: {str(e)}"}), 500


# Yeni endpoint'ler - ChromaDB ve Embedder yönetimi

@app.route("/api/admin/chromadb/info", methods=["GET"])
def admin_chromadb_info():
    """ChromaDB bilgilerini döner"""
    try:
        collection_info = chroma_manager.get_collection_info()
        stats = chroma_manager.get_stats()

        return jsonify(
            {"collection_info": collection_info, "stats": stats, "status": "active"}
        )
    except Exception as e:
        return jsonify({"error": f"ChromaDB bilgisi alınamadı: {str(e)}"}), 500


@app.route("/api/admin/chromadb/backup", methods=["POST"])
def admin_chromadb_backup():
    """ChromaDB backup oluşturur"""
    try:
        data = request.get_json() or {}
        backup_name = data.get("name", None)

        backup_path = chroma_manager.create_backup(backup_name)

        return jsonify(
            {"backup_path": backup_path, "message": "Backup başarıyla oluşturuldu"}
        )
    except Exception as e:
        return jsonify({"error": f"Backup hatası: {str(e)}"}), 500


@app.route("/api/admin/chromadb/optimize", methods=["POST"])
def admin_chromadb_optimize():
    """ChromaDB optimizasyonu yapar"""
    try:
        result = chroma_manager.optimize_collection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Optimizasyon hatası: {str(e)}"}), 500


@app.route("/api/admin/embedder/info", methods=["GET"])
def admin_embedder_info():
    """Embedder bilgilerini döner"""
    try:
        info = embedder.get_model_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": f"Embedder bilgisi alınamadı: {str(e)}"}), 500


@app.route("/api/admin/embedder/benchmark", methods=["POST"])
def admin_embedder_benchmark():
    """Embedder performans testi yapar"""
    try:
        data = request.get_json() or {}
        test_texts = data.get(
            "test_texts",
            [
                "Bu bir test cümlesidir.",
                "Belgede belirtilen kurallar nelerdir?",
                "Bu işlem için gerekli belgeler nelerdir?",
            ],
        )

        results = embedder.benchmark_models(test_texts)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Benchmark hatası: {str(e)}"}), 500


@app.route("/api/admin/embedder/cache/clear", methods=["POST"])
def admin_embedder_cache_clear():
    """Embedder cache'ini temizler"""
    try:
        if embedder.cache:
            embedder.cache.clear()
            return jsonify({"message": "Cache başarıyla temizlendi"})
        else:
            return jsonify({"message": "Cache aktif değil"})
    except Exception as e:
        return jsonify({"error": f"Cache temizleme hatası: {str(e)}"}), 500


@app.route("/api/admin/embedder/cache/stats", methods=["GET"])
def admin_embedder_cache_stats():
    """Embedder cache istatistiklerini döner"""
    try:
        if embedder.cache:
            stats = embedder.cache.get_stats()
            return jsonify(stats)
        else:
            return jsonify({"message": "Cache aktif değil"})
    except Exception as e:
        return jsonify({"error": f"Cache istatistikleri alınamadı: {str(e)}"}), 500


@app.route("/api/admin/system/status", methods=["GET"])
def admin_system_status():
    """Sistem durumu özeti"""
    try:
        # Dosya sayıları
        total_files = (
            len([f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)])
            if os.path.exists(UPLOAD_FOLDER)
            else 0
        )

        # ChromaDB stats
        chromadb_stats = chroma_manager.get_stats()

        # Embedder stats
        embedder_info = embedder.get_model_info()

        # Disk usage
        chroma_size = chromadb_stats.get("index_size_mb", 0)
        upload_size = 0
        if os.path.exists(UPLOAD_FOLDER):
            for f in os.listdir(UPLOAD_FOLDER):
                path = os.path.join(UPLOAD_FOLDER, f)
                if os.path.isfile(path):
                    upload_size += os.path.getsize(path)
        upload_size_mb = upload_size / (1024 * 1024)

        return jsonify(
            {
                "files": {
                    "total_uploaded": total_files,
                    "upload_size_mb": round(upload_size_mb, 2),
                },
                "chromadb": {
                    "total_chunks": chromadb_stats.get("total_chunks", 0),
                    "unique_sources": chromadb_stats.get("unique_sources", 0),
                    "index_size_mb": chroma_size,
                    "last_updated": chromadb_stats.get("last_updated"),
                },
                "embedder": {
                    "model": embedder_info.get("primary_model"),
                    "device": embedder_info.get("device"),
                    "cache_enabled": embedder_info.get("cache_enabled", False),
                    "cache_size": embedder_info.get("cache_stats", {}).get(
                        "total_embeddings", 0
                    ),
                },
                "system": {
                    "total_disk_usage_mb": round(chroma_size + upload_size_mb, 2),
                    "status": "healthy",
                },
            }
        )
    except Exception as e:
        return jsonify({"error": f"Sistem durumu alınamadı: {str(e)}"}), 500


@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    """Soru istatistikleri (frontend uyumlu)"""
    try:
        from question_db import (
            get_total_questions,
            get_top_sources,
            get_top_questions_with_topics,
            get_daily_user_stats,
            get_total_entry_count,
            clean_obsolete_sources,
            update_missing_keywords,
        )
        import sqlite3
        from datetime import datetime, timedelta

        # Önce eski kayıtları temizle
        clean_obsolete_sources()

        # Toplam soru sayısı
        total_questions = get_total_questions()

        # Kullanıcı istatistikleri
        user_stats = get_daily_user_stats()
        total_entries = get_total_entry_count()

        # En çok kullanılan 5 kaynak (kaynak + anahtar kelime + count)
        top_sources = get_top_sources(5)
        top_sources_list = [
            {"source": source, "keyword": keyword, "count": count}
            for source, keyword, count in top_sources
        ]

        # En çok sorulan 5 soru (topic ile birlikte)
        top_questions = get_top_questions_with_topics(5)
        top_questions_list = [
            {
                "question": item["question"],
                "answer": item["answer"],
                "count": item["count"],
                "topic": item["topic"],
            }
            for item in top_questions
        ]

        # Günlük soru sayısı (bugün)
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect("questions.db")
            c = conn.cursor()
            c.execute(
                """
                SELECT COUNT(*) FROM questions
                WHERE DATE(created_at) = ?
            """,
                (today,),
            )
            daily_questions = c.fetchone()[0]
            conn.close()
        except Exception as e:
            daily_questions = 0
            print(f"Günlük soru sayısı alınamadı: {e}")

        return jsonify(
            {
                "totalQuestions": total_questions,
                "dailyQuestions": daily_questions,
                "dailyUsers": user_stats["daily_users"],
                "totalUsers": user_stats["total_users"],
                "totalEntries": total_entries,
                "weeklyActivity": user_stats["weekly_activity"],
                "topSources": top_sources_list,
                "topQuestions": top_questions_list,
            }
        )

    except Exception as e:
        return jsonify({"error": f"Soru istatistikleri alınamadı: {str(e)}"}), 500


@app.route("/api/admin/upload_and_process", methods=["POST"])
def admin_upload_and_process():
    """
    Dosya yükle, chunkla, embedle ve ChromaDB'ye ekle (tam otomatik pipeline)
    """
    try:
        file = request.files.get("file")
        keyword = request.form.get("keyword", "")
        if not file:
            return jsonify({"error": "Dosya bulunamadı"}), 400

        # 1. Dosyayı uploads klasörüne kaydet
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        # 2. uploads klasörünü chunkla ve uploads_base.json'u güncelle
        processor = AdvancedDocumentProcessor()
        data = processor.process_documents(save_path, keyword=keyword)
        if not data:
            return jsonify({"error": "Chunklama başarısız"}), 500

        # uploads_base.json'u güncelle (duplicate dosya engelle)
        uploads_base_path = "uploads_base.json"
        if os.path.exists(uploads_base_path):
            with open(uploads_base_path, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        else:
            all_data = []
        # Duplicate filename'leri çıkar
        new_filenames = {item.get("filename") for item in data}
        all_data = [
            item for item in all_data if item.get("filename") not in new_filenames
        ]
        all_data.extend(data)
        with open(uploads_base_path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        # 3. Embedding işlemini tetikle ve uploads_with_embed.json'u güncelle
        from embedder import process_documents_with_embeddings

        # Config'den model adını al ve doğru kullan
        embedding_model = config.EMBEDDING_MODEL if hasattr(config, 'EMBEDDING_MODEL') else "paraphrase-multilingual-MiniLM-L12-v2"
        
        stats = process_documents_with_embeddings(
            input_file="uploads_base.json",
            output_file="uploads_with_embed.json",
            model_config={
                "model": embedding_model,  # "primary_model" yerine "model" kullan
                "use_ensemble": False,
                "use_cache": True,
                "batch_size": 50,
            },
        )
        # Embedding sonrası uploads_with_embed.json'da dosya var mı kontrol et, yoksa hata dön
        with open("uploads_with_embed.json", "r", encoding="utf-8") as f:
            embed_data = json.load(f)
        if not any(item.get("filename") == filename for item in embed_data):
            return (
                jsonify(
                    {
                        "error": "Embedding sonrası dosya uploads_with_embed.json'a eklenemedi."
                    }
                ),
                500,
            )

        # 4. ChromaDB'ye ekle
        chroma_manager = ChromaDBManager()
        chroma_manager.add_documents_batch(
            embed_data, batch_size=1000, skip_duplicates=True
        )

        # 5. Dosyayı işlenmiş ana klasöre (docs/) taşı
        docs_folder = os.path.join(os.getcwd(), "docs")
        os.makedirs(docs_folder, exist_ok=True)
        try:
            import shutil

            shutil.move(save_path, os.path.join(docs_folder, filename))
        except Exception as e:
            app.logger.warning(f"Dosya docs klasörüne taşınamadı: {e}")

        # 6. uploads_base.json içeriğini enhanced_document_data.json'a EKLE (mevcut veriyi koruyarak ve keyword'ü koruyarak)
        enhanced_base_path = "enhanced_document_data.json"
        try:
            if os.path.exists("uploads_base.json"):
                with open("uploads_base.json", "r", encoding="utf-8") as f:
                    uploads_base_data = json.load(f)
            else:
                uploads_base_data = []
            if os.path.exists(enhanced_base_path):
                with open(enhanced_base_path, "r", encoding="utf-8") as f:
                    enhanced_base_data = json.load(f)
            else:
                enhanced_base_data = []
            # uploads_base.json içeriğini mevcut enhanced veriye ekle (duplicate filename engelle)
            existing_filenames = {item.get("filename") for item in enhanced_base_data}
            new_items = []
            for item in uploads_base_data:
                if item.get("filename") not in existing_filenames:
                    # Eğer anahtar kelime frontend'den geldiyse ve item'da yoksa ekle
                    if not item.get("keyword") and keyword:
                        item["keyword"] = keyword
                    new_items.append(item)
            enhanced_base_data.extend(new_items)
            with open(enhanced_base_path, "w", encoding="utf-8") as f:
                json.dump(enhanced_base_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            app.logger.error(f"enhanced_document_data.json güncellenemedi: {e}")

        # 7. uploads_with_embed.json içeriğini enhanced_document_data_with_embeddings.json'a EKLE (mevcut veriyi koruyarak ve keyword'ü koruyarak)
        enhanced_embed_path = "enhanced_document_data_with_embeddings.json"
        try:
            if os.path.exists("uploads_with_embed.json"):
                with open("uploads_with_embed.json", "r", encoding="utf-8") as f:
                    uploads_embed_data = json.load(f)
            else:
                uploads_embed_data = []
            if os.path.exists(enhanced_embed_path):
                with open(enhanced_embed_path, "r", encoding="utf-8") as f:
                    enhanced_embed_data = json.load(f)
            else:
                enhanced_embed_data = []
            existing_filenames = {item.get("filename") for item in enhanced_embed_data}
            new_items = []
            for item in uploads_embed_data:
                if item.get("filename") not in existing_filenames:
                    if not item.get("keyword") and keyword:
                        item["keyword"] = keyword
                    new_items.append(item)
            enhanced_embed_data.extend(new_items)
            with open(enhanced_embed_path, "w", encoding="utf-8") as f:
                json.dump(enhanced_embed_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            app.logger.error(
                f"enhanced_document_data_with_embeddings.json güncellenemedi: {e}"
            )

        # 8. uploads_base.json ve uploads_with_embed.json dosyalarını sil
        try:
            if os.path.exists("uploads_base.json"):
                os.remove("uploads_base.json")
            if os.path.exists("uploads_with_embed.json"):
                os.remove("uploads_with_embed.json")
        except Exception as e:
            app.logger.error(
                f"uploads_base.json veya uploads_with_embed.json silinemedi: {e}"
            )

        # 9. uploads klasöründeki dosyaları docs klasörüne taşı
        docs_folder = os.path.join(os.getcwd(), "docs")
        os.makedirs(docs_folder, exist_ok=True)
        try:
            for f in os.listdir(UPLOAD_FOLDER):
                src_path = os.path.join(UPLOAD_FOLDER, f)
                dst_path = os.path.join(docs_folder, f)
                if os.path.isfile(src_path):
                    try:
                        import shutil

                        shutil.move(src_path, dst_path)
                    except Exception as e:
                        app.logger.warning(f"{f} docs klasörüne taşınamadı: {e}")
        except Exception as e:
            app.logger.error(f"uploads klasöründen docs klasörüne taşıma hatası: {e}")

        return jsonify({"success": True, "filename": filename, "stats": stats})

    except Exception as e:
        app.logger.error(f"Pipeline hata: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/clear_questions", methods=["POST"])
def clear_questions():
    """Tüm soru veritabanını temizler"""
    try:
        from question_db import clear_all_questions

        clear_all_questions()
        return jsonify({"message": "Tüm sorular başarıyla temizlendi"})
    except Exception as e:
        return jsonify({"error": f"Soru temizleme hatası: {str(e)}"}), 500


@app.route("/api/admin/clear_questions_advanced", methods=["POST"])
def clear_questions_advanced():
    """Gelişmiş soru silme - dönem bazında"""
    try:
        data = request.get_json()
        period_type = data.get("period_type", "all")  # "all" veya "today"

        from question_db import clear_questions_by_period

        affected_rows = clear_questions_by_period(period_type)

        if period_type == "today":
            message = f"Bugünkü {affected_rows} soru ve kullanıcı oturumu silindi"
        else:
            message = f"Tüm {affected_rows} soru ve veri silindi"

        return jsonify(
            {
                "message": message,
                "affected_rows": affected_rows,
                "period_type": period_type,
            }
        )

    except Exception as e:
        return jsonify({"error": f"Gelişmiş silme hatası: {str(e)}"}), 500


@app.route("/api/user/session", methods=["POST"])
def track_user_session():
    """Kullanıcı oturumunu takip et"""
    try:
        data = request.get_json()
        user_id = data.get("user_id", "anonymous")

        from question_db import track_user_session

        track_user_session(user_id, question_asked=False)

        return jsonify({"status": "session_tracked"}), 200
    except Exception as e:
        return jsonify({"error": f"Session tracking hatası: {str(e)}"}), 500


def update_stats_json():
    """Stats.json dosyasını güncel verilerle güncelle - sadece mevcut dosyaları dahil et"""
    try:
        from question_db import (
            get_total_questions,
            get_top_sources,
            get_top_questions_by_similarity,
        )

        # Mevcut istatistikleri al (sadece mevcut dosyalardan)
        total_questions = get_total_questions()
        top_sources = get_top_sources(5)  # Artık (source, keyword, count, unikys_name) tuple'ı dönüyor
        top_questions = get_top_questions_by_similarity(5)

        # Stats verisini hazırla
        stats_data = {
            "totalQuestions": total_questions,
            "uniqueQuestions": total_questions,  # Şimdilik total ile aynı
            "topSources": [
                {"source": source, "keyword": keyword, "count": count, "unikys_name": unikys_name}
                for source, keyword, count, unikys_name in top_sources
            ],
            "topQuestions": [
                {"question": question, "count": count}
                for question, answer, count in top_questions
            ],
            "lastUpdated": dt.now().isoformat(),
        }

        # stats.json dosyasını güncelle
        with open("stats.json", "w", encoding="utf-8") as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Stats.json güncellenirken hata: {e}")


@app.route("/api/admin/daily-questions", methods=["GET"])
def get_daily_questions():
    """Bugün sorulan soruları listele - kaynak bilgileriyle birlikte"""
    try:
        from question_db import get_daily_questions_paginated
        import sqlite3
        from datetime import datetime

        # Query parametreleri
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))

        # Günlük soruları al
        result = get_daily_questions_paginated(page, limit)

        return jsonify(
            {
                "questions": result["questions"],
                "totalPages": result["total_pages"],
                "currentPage": page,
                "totalQuestions": result["total_questions"],
            }
        )

    except Exception as e:
        return jsonify({"error": f"Günlük sorular alınamadı: {str(e)}"}), 500


@app.route("/api/admin/all-questions", methods=["GET"])
def get_all_questions():
    """Tüm soruları listele - en çok sorulan sorular için"""
    try:
        from question_db import get_all_questions_paginated
        import sqlite3
        from datetime import datetime

        # Query parametreleri
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))

        # Tüm soruları al
        result = get_all_questions_paginated(page, limit)

        return jsonify(
            {
                "questions": result["questions"],
                "totalPages": result["total_pages"],
                "currentPage": page,
                "totalQuestions": result["total_questions"],
            }
        )

    except Exception as e:
        return jsonify({"error": f"Tüm sorular alınamadı: {str(e)}"}), 500


if __name__ == "__main__":
    print("🚀 RAG Chatbot API başlatılıyor...")
    print("📍 API URL: http://localhost:5001")
    print("🔗 Health Check: http://localhost:5001/api/health")
    print(f"📁 Upload Folder: {UPLOAD_FOLDER}")
    print(f"📊 Embeddings Folder: {EMBEDDINGS_FOLDER}")
    print(f"🗄️ ChromaDB Path: {chroma_manager.chroma_path}")
    print(f"🗃️ Collection: {chroma_manager.collection_name}")
    print()
    print("🔧 KONFIGÜRASYON:")
    print(f"   🤖 Embedding Model: {EMBEDDING_MODEL}")
    print(f"   � Cache Enabled: {embedder.cache is not None}")
    print(f"   📏 Max Chunk Size: {config.MAX_CHUNK_SIZE}")
    print(f"   🔗 Chunk Overlap: {config.CHUNK_OVERLAP}")
    print()

    # Sistem durumu
    try:
        initialize_database()  # Veritabanını başlat
        stats = chroma_manager.get_stats()
        collection_info = chroma_manager.get_collection_info()
        print("📈 MEVCUT DURUM:")
        print(f"   📊 Chunk sayısı: {stats.get('total_chunks', 0):,}")
        print(f"   📚 Kaynak dosya sayısı: {collection_info.get('source_count', 0)}")
        print(f"   💿 Index boyutu: {stats.get('index_size_mb', 0):.2f} MB")

        # Dosya türü dağılımı
        file_types = collection_info.get("file_types", [])
        if file_types:
            print(f"   📄 Dosya türleri: {', '.join(file_types)}")

    except Exception as e:
        print(f"⚠️ Sistem durumu alınamadı: {e}")

    print("\n" + "=" * 50)
    print("API hazır! Admin panel: http://localhost:3000")
    print("=" * 50 + "\n")

    # Basit admin rotalarını ekle
    import admin_auth

    @app.route("/admin/login", methods=["POST"])
    def admin_login():
        """Admin giriş"""
        try:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return jsonify({"error": "Kullanıcı adı ve şifre gerekli"}), 400

            ip_address = request.environ.get("REMOTE_ADDR")
            user_agent = request.headers.get("User-Agent")

            result = admin_auth.authenticate_admin(
                username, password, ip_address, user_agent
            )

            if result["success"]:
                return jsonify(
                    {
                        "success": True,
                        "message": result["message"],
                        "token": result["session_token"],
                        "admin_id": result["admin_id"],
                        "username": result["username"],
                        "expires_at": result["expires_at"],
                    }
                )
            else:
                return jsonify({"error": result["message"]}), 401

        except Exception as e:
            return jsonify({"error": f"Giriş hatası: {str(e)}"}), 500

    @app.route("/admin/verify", methods=["POST"])
    def admin_verify():
        """Admin token doğrulama"""
        try:
            # Token'ı hem Authorization header'dan hem body'den al
            token = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
            else:
                data = request.get_json() or {}
                token = data.get("token")

            if not token:
                return jsonify({"error": "Token gerekli"}), 401

            result = admin_auth.verify_session(token)

            if result["valid"]:
                return jsonify(
                    {
                        "valid": True,
                        "admin_id": result["admin_id"],
                        "username": result["username"],
                    }
                )
            else:
                return jsonify({"valid": False, "message": result["message"]}), 401

        except Exception as e:
            return jsonify({"error": f"Token doğrulama hatası: {str(e)}"}), 500

    @app.route("/admin/logout", methods=["POST"])
    def admin_logout():
        """Admin çıkış"""
        try:
            data = request.get_json()
            token = data.get("token")

            if token:
                admin_auth.logout_admin(token)

            return jsonify({"success": True, "message": "Başarıyla çıkış yapıldı"})

        except Exception as e:
            return jsonify({"error": f"Çıkış hatası: {str(e)}"}), 500

    # Admin veritabanını başlat
    admin_auth.init_admin_db()
    print("✅ Admin login sistemi aktif!")

    app.run(debug=True, host="0.0.0.0", port=5001)