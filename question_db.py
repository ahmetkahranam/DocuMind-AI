def delete_questions_by_source_file(filename):
    """Belirli bir dosyaya ait tüm soruları ve ilişkili verileri siler"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Önce question_sources tablosundan sil
    c.execute("DELETE FROM question_sources WHERE source_file = ?", (filename,))
    # Sonra questions tablosundan sil
    c.execute("DELETE FROM questions WHERE source_file = ?", (filename,))
    # Son olarak orphan olmuş question_similarity kayıtlarını temizle
    c.execute("DELETE FROM question_similarity WHERE question_id_1 NOT IN (SELECT id FROM questions) OR question_id_2 NOT IN (SELECT id FROM questions)")
    conn.commit()
    conn.close()
    print(f"✅ {filename} dosyasına ait tüm sorular ve ilişkili veriler silindi.")
import sqlite3
import os
from datetime import datetime
import json

DB_PATH = "questions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT,
        source_file TEXT,
        source_keyword TEXT,
        topic TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Mevcut tabloya topic sütunu ekle (eğer yoksa)
    try:
        c.execute("ALTER TABLE questions ADD COLUMN topic TEXT")
    except sqlite3.OperationalError:
        pass  # Sütun zaten varsa hata verme
    c.execute("""
    CREATE TABLE IF NOT EXISTS question_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        source_file TEXT,
        FOREIGN KEY(question_id) REFERENCES questions(id),
        UNIQUE(question_id, source_file)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS question_similarity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id_1 INTEGER,
        question_id_2 INTEGER,
        similarity REAL,
        FOREIGN KEY(question_id_1) REFERENCES questions(id),
        FOREIGN KEY(question_id_2) REFERENCES questions(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        session_date DATE DEFAULT (date('now')),
        first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_questions INTEGER DEFAULT 0,
        UNIQUE(user_id, session_date)
    )
    """)
    conn.commit()
    conn.close()

def detect_topic(question):
    """Sorudan topic/konu tespit et"""
    question_lower = question.lower()
    
    # Konu tespit kuralları
    topics = {
        "bilgisayar_laboratuvari": ["bilgisayar laboratuvar", "lab", "laboratuvar", "sınav", "su getir", "yiyecek", "içecek"],
        "eduroam": ["eduroam", "wifi", "internet", "bağlantı", "şifre", "parola", "android", "eap", "phase"],
        "sinav_kurallari": ["sınav", "kurall", "yapılacak", "yasaklı", "izin"],
        "kimlik_belgesi": ["kimlik", "belge", "öğrenci kart", "tc kimlik"],
        "kayit_isleri": ["kayıt", "ders", "kredi", "not", "transkript"],
        "yemek": ["yemek", "kafeterya", "mensa", "beslenme"],
        "konaklama": ["yurt", "barınma", "konaklama", "ev"],
        "ulasim": ["otobüs", "ulaşım", "servis", "ring"],
        "burs": ["burs", "kredi", "öğrenim", "ücret"],
        "ogrenci_isleri": ["öğrenci işleri", "işlem", "başvuru", "belge"]
    }
    
    for topic, keywords in topics.items():
        for keyword in keywords:
            if keyword in question_lower:
                return topic
    
    return "genel"

def add_question(question, answer=None, source_file=None, source_keyword=None, topic=None):
    """Soru ekle - topic otomatik tespit"""
    if not topic:
        topic = detect_topic(question)

    # source_file varsa sadece dosya adını kaydet
    if source_file:
        import os
        source_file = os.path.basename(source_file).lower()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO questions (question, answer, source_file, source_keyword, topic) VALUES (?, ?, ?, ?, ?)", 
              (question, answer, source_file, source_keyword, topic))
    qid = c.lastrowid
    conn.commit()
    conn.close()
    return qid

def add_question_source(question_id, source_file):
    if not source_file or not isinstance(source_file, str) or not source_file.strip():
        return  # Boş veya geçersiz kaynak eklenmesin
    import os
    source_file = os.path.basename(source_file).lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO question_sources (question_id, source_file) VALUES (?, ?)", (question_id, source_file))
        conn.commit()
    except Exception as e:
        print(f"⚠️ add_question_source hatası: {e}")
    finally:
        conn.close()

def add_similarity(qid1, qid2, similarity):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO question_similarity (question_id_1, question_id_2, similarity) VALUES (?, ?, ?)", (qid1, qid2, similarity))
    conn.commit()
    conn.close()

def get_total_questions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM questions")
    total = c.fetchone()[0]
    conn.close()
    return total

def clear_all_questions():
    """Tüm soruları ve ilişkili verileri siler"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM question_similarity")
    c.execute("DELETE FROM question_sources")
    c.execute("DELETE FROM questions")
    conn.commit()
    conn.close()
    print("✅ Tüm sorular temizlendi")

def clear_questions_by_period(period_type="all"):
    """Soruları dönem bazında temizle"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if period_type == "today":
        c.execute("DELETE FROM questions WHERE DATE(created_at) = DATE('now')")
        c.execute("DELETE FROM user_sessions WHERE session_date = DATE('now')")
    elif period_type == "all":
        c.execute("DELETE FROM questions")
        c.execute("DELETE FROM user_sessions")
        c.execute("DELETE FROM question_sources")
        c.execute("DELETE FROM question_similarity")
    
    conn.commit()
    affected_rows = c.rowcount
    conn.close()
    return affected_rows

def get_total_unique_questions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT question) FROM questions")
    total = c.fetchone()[0]
    conn.close()
    return total

def get_available_filenames():
    """Mevcut dosya isimlerini enhanced_document_data.json'dan al"""
    filenames = set()
    # enhanced_document_data.json
    try:
        with open("enhanced_document_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            filenames.update(item["filename"].lower() for item in data if "filename" in item)
    except Exception as e:
        print(f"Enhanced document data okunamadı: {e}")
    # data.json
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            filenames.update(item["filename"].lower() for item in data if "filename" in item)
    except Exception as e:
        print(f"data.json okunamadı: {e}")
    return list(filenames)

def get_top_sources(limit=5):
    """Sadece mevcut dosyalardan en çok kullanılan kaynakları al - aynı dosya için tek kayıt"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Mevcut dosya isimlerini al
    available_files = get_available_filenames()
    print(f"[DEBUG] available_files: {available_files}")

    # Hem tam dosya adı hem de sadece dosya adı (basename) ile eşleşme için iki set oluştur
    available_files_set = set(f.lower() for f in available_files)
    available_basenames = set(os.path.basename(f).lower() for f in available_files)

    if not available_files:
        conn.close()
        print("[DEBUG] Hiç mevcut dosya yok!")
        return [("(Hiç kaynak kullanılmadı)", "", 0)]
    
    # enhanced_document_data.json ve data.json'dan anahtar kelimeleri al
    file_keywords = {}
    for json_file in ["enhanced_document_data.json", "data.json"]:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                document_data = json.load(f)
                for item in document_data:
                    fname = item.get("filename")
                    if fname:
                        fname_lower = fname.lower()
                        if "keyword" in item:
                            file_keywords[fname_lower] = item.get("keyword", "")
        except Exception as e:
            print(f"{json_file} okunamadı: {e}")
    
    # Placeholder'ları oluştur
    # Tüm source_file'ları ve sayısını çek
    c.execute("""
        SELECT source_file, COUNT(*) as cnt
        FROM questions
        WHERE source_file IS NOT NULL AND source_file != ''
        GROUP BY source_file
        ORDER BY cnt DESC
    """)
    all_results = c.fetchall()
    print(f"[DEBUG] ALL SQL results: {all_results}")

    # Sadece json'daki dosyalarla eşleşenleri al (tam veya basename ile)
    filtered_results = []
    for source_file, cnt in all_results:
        sf_lower = source_file.lower()
        sf_base = os.path.basename(source_file).lower()
        if sf_lower in available_files_set or sf_base in available_basenames:
            filtered_results.append((source_file, cnt))

    # Limitle
    results = filtered_results[:limit]
    print(f"[DEBUG] Filtered results: {results}")
    conn.close()
    
    if not results:
        return [("(Hiç kaynak kullanılmadı)", "", 0, "")]
    
    # Sonuçları enhanced_document_data.json'dan gelen anahtar kelimelerle birleştir
    final_results = []
    for source_file, count in results:
        keyword = file_keywords.get(source_file.lower(), "")
        final_results.append((source_file, keyword, count))
    return final_results

def get_top_questions_by_similarity(limit=5):
    """Benzer soruları gruplar ve en çok sorulan grupları döndürür"""
    import difflib
    from collections import defaultdict
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tüm soruları ve cevaplarını al
    c.execute("SELECT question, answer, COUNT(*) as cnt FROM questions GROUP BY question, answer")
    all_questions = c.fetchall()
    conn.close()
    
    if not all_questions:
        return []
    
    # Benzer soruları grupla
    question_groups = defaultdict(list)
    processed = set()
    
    for i, (question, answer, count) in enumerate(all_questions):
        if i in processed:
            continue
            
        # Bu soru için grup oluştur
        group_key = question.lower().strip()
        group_questions = [(question, answer, count)]
        processed.add(i)
        
        # Diğer sorularla benzerlik kontrolü
        for j, (other_question, other_answer, other_count) in enumerate(all_questions):
            if j in processed or i == j:
                continue
                
            # Benzerlik oranını hesapla
            similarity = difflib.SequenceMatcher(
                None, 
                question.lower().strip(), 
                other_question.lower().strip()
            ).ratio()
            
            # %75 ve üzeri benzerlik varsa aynı grup
            if similarity >= 0.75:
                group_questions.append((other_question, other_answer, other_count))
                processed.add(j)
        
        # Grup toplamını hesapla
        total_count = sum(q[2] for q in group_questions)
        
        # En çok sorulan soruyu temsil edici olarak seç
        representative = max(group_questions, key=lambda x: x[2])
        
        question_groups[group_key] = {
            'question': representative[0],
            'answer': representative[1], 
            'count': total_count,
            'variants': len(group_questions)
        }
    
    # Sayıya göre sırala ve limit kadar al
    sorted_groups = sorted(
        question_groups.values(), 
        key=lambda x: x['count'], 
        reverse=True
    )
    
    return [(g['question'], g['answer'], g['count']) for g in sorted_groups[:limit]]

def track_user_session(user_id, question_asked=False):
    """Kullanıcı oturumunu takip et"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().date()
    
    try:
        # Bugün için session var mı kontrol et
        c.execute("""
            SELECT id, total_questions FROM user_sessions 
            WHERE user_id = ? AND session_date = ?
        """, (user_id, today))
        
        result = c.fetchone()
        
        if result:
            # Mevcut session'ı güncelle
            session_id, current_questions = result
            new_question_count = current_questions + (1 if question_asked else 0)
            
            c.execute("""
                UPDATE user_sessions 
                SET last_activity = CURRENT_TIMESTAMP, total_questions = ?
                WHERE id = ?
            """, (new_question_count, session_id))
        else:
            # Yeni session oluştur
            c.execute("""
                INSERT INTO user_sessions (user_id, session_date, total_questions)
                VALUES (?, ?, ?)
            """, (user_id, today, 1 if question_asked else 0))
        
        conn.commit()
    except Exception as e:
        print(f"Session tracking hatası: {e}")
    finally:
        conn.close()

def get_daily_user_stats():
    """Günlük kullanıcı istatistiklerini getir"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Bugünkü aktif kullanıcı sayısı
        c.execute("""
            SELECT COUNT(DISTINCT user_id) as daily_users
            FROM user_sessions 
            WHERE session_date = date('now')
        """)
        daily_users = c.fetchone()[0] or 0
        
        # Toplam benzersiz kullanıcı sayısı
        c.execute("""
            SELECT COUNT(DISTINCT user_id) as total_users
            FROM user_sessions
        """)
        total_users = c.fetchone()[0] or 0
        
        # Son 7 günlük aktivite
        c.execute("""
            SELECT session_date, COUNT(DISTINCT user_id) as user_count
            FROM user_sessions 
            WHERE session_date >= date('now', '-7 days')
            GROUP BY session_date 
            ORDER BY session_date DESC
        """)
        weekly_activity = c.fetchall()
        
        # Bugünkü toplam soru sayısı
        c.execute("""
            SELECT SUM(total_questions) as daily_questions
            FROM user_sessions 
            WHERE session_date = date('now')
        """)
        daily_questions = c.fetchone()[0] or 0
        
        return {
            'daily_users': daily_users,
            'total_users': total_users,
            'daily_questions': daily_questions,
            'weekly_activity': weekly_activity
        }
    except Exception as e:
        print(f"İstatistik hatası: {e}")
        return {
            'daily_users': 0,
            'total_users': 0, 
            'daily_questions': 0,
            'weekly_activity': []
        }
    finally:
        conn.close()

def get_total_entry_count():
    """Toplam giriş sayısını getir"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute("SELECT COUNT(*) as total_entries FROM user_sessions")
        result = c.fetchone()
        return result[0] if result else 0
    except Exception as e:
        print(f"Toplam giriş sayısı hatası: {e}")
        return 0
    finally:
        conn.close()

def get_top_questions_with_topics(limit=5):
    """Topic'lere göre gruplandırılmış en çok sorulan soruları döndürür"""
    import difflib
    from collections import defaultdict
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tüm soruları topic ile birlikte al
    c.execute("SELECT question, answer, topic, COUNT(*) as cnt FROM questions GROUP BY question, answer, topic")
    all_questions = c.fetchall()
    conn.close()
    
    if not all_questions:
        return []
    
    # Topic'lere göre grupla
    topic_groups = defaultdict(list)
    
    for question, answer, topic, count in all_questions:
        topic = topic or "genel"
        topic_groups[topic].append((question, answer, count))
    
    # Her topic için benzer soruları grupla
    final_results = []
    
    for topic, questions in topic_groups.items():
        if not questions:
            continue
            
        # Bu topic içinde benzer soruları grupla
        processed = set()
        grouped_questions = []
        
        for i, (question, answer, count) in enumerate(questions):
            if i in processed:
                continue
                
            group_questions = [(question, answer, count)]
            processed.add(i)
            
            # Aynı topic içindeki diğer sorularla benzerlik kontrolü
            for j, (other_question, other_answer, other_count) in enumerate(questions):
                if j in processed or i == j:
                    continue
                
                similarity = difflib.SequenceMatcher(
                    None, 
                    question.lower().strip(), 
                    other_question.lower().strip()
                ).ratio()
                
                if similarity >= 0.7:  # %70 benzerlik
                    group_questions.append((other_question, other_answer, other_count))
                    processed.add(j)
            
            # Grup toplamını hesapla
            total_count = sum(q[2] for q in group_questions)
            
            # En çok sorulan soruyu temsil edici seç
            representative = max(group_questions, key=lambda x: x[2])
            
            grouped_questions.append({
                'question': f"[{topic.replace('_', ' ').title()}] {representative[0]}",
                'answer': representative[1],
                'count': total_count,
                'topic': topic,
                'variants': len(group_questions)
            })
        
        final_results.extend(grouped_questions)
    
    # Sayıya göre sırala ve limit kadar al
    final_results.sort(key=lambda x: x['count'], reverse=True)
    return final_results[:limit]

def clean_obsolete_sources():
    """Artık mevcut olmayan dosyalara ait kayıtları temizle ve anahtar kelimeleri güncelle"""
    try:
        available_files = get_available_filenames()
        
        if not available_files:
            print("Mevcut dosya bulunamadı, temizlik yapılmıyor.")
            return
            
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Mevcut olmayan kaynak dosyalarına sahip kayıtları bul
        placeholders = ','.join(['?' for _ in available_files])
        c.execute(f"""
        SELECT COUNT(*) FROM questions 
        WHERE source_file IS NOT NULL 
        AND source_file != '' 
        AND source_file NOT IN ({placeholders})
        """, available_files)
        
        obsolete_count = c.fetchone()[0]
        
        if obsolete_count > 0:
            print(f"Temizlenecek eski kayıt sayısı: {obsolete_count}")
            
            # Eski kayıtları sil
            c.execute(f"""
            DELETE FROM questions 
            WHERE source_file IS NOT NULL 
            AND source_file != '' 
            AND source_file NOT IN ({placeholders})
            """, available_files)
            
            conn.commit()
            print(f"{obsolete_count} eski kayıt temizlendi.")
        else:
            print("Temizlenecek eski kayıt bulunamadı.")
            
        conn.close()
        
        # Anahtar kelimeleri güncelle
        update_missing_keywords()
        
    except Exception as e:
        print(f"Eski kayıt temizlenirken hata: {e}")

def update_missing_keywords():
    """Eksik anahtar kelimeleri enhanced_document_data.json'dan güncelle"""
    try:
        # Enhanced document data'dan anahtar kelimeleri al
        with open("enhanced_document_data.json", "r", encoding="utf-8") as f:
            document_data = json.load(f)
            file_keywords = {item["filename"]: item.get("keyword", "") for item in document_data}
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        updated_count = 0
        
        for filename, keyword in file_keywords.items():
            if keyword:  # Anahtar kelime varsa
                # Bu dosya için boş anahtar kelimeli kayıtları güncelle
                c.execute("""
                UPDATE questions 
                SET source_keyword = ? 
                WHERE source_file = ? 
                AND (source_keyword IS NULL OR source_keyword = '')
                """, (keyword, filename))
                
                updated_count += c.rowcount
        
        conn.commit()
        conn.close()
        
        if updated_count > 0:
            print(f"{updated_count} kayıt için anahtar kelime güncellendi.")
        else:
            print("Güncellenecek anahtar kelime bulunamadı.")
            
    except Exception as e:
        print(f"Anahtar kelime güncellenirken hata: {e}")

def get_daily_questions_paginated(page=1, limit=10):
    """Bugün sorulan soruları sayfalayarak al - kaynak bilgileriyle birlikte"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        offset = (page - 1) * limit
        
        # Enhanced document data'dan anahtar kelimeleri al
        file_keywords = {}
        try:
            with open("enhanced_document_data.json", "r", encoding="utf-8") as f:
                document_data = json.load(f)
                file_keywords = {item["filename"]: item.get("keyword", "") for item in document_data}
        except Exception as e:
            print(f"Enhanced document data okunamadı: {e}")
        
        # Bugün sorulan sorular - aynı soruları grupla (case-insensitive)
        c.execute("""
        SELECT LOWER(TRIM(question)) as normalized_question, 
               question as original_question,
               answer, 
               source_file,
               topic,
               COUNT(*) as count, 
               MIN(created_at) as first_asked
        FROM questions 
        WHERE DATE(created_at) = ?
        GROUP BY LOWER(TRIM(question))
        ORDER BY count DESC, first_asked DESC
        LIMIT ? OFFSET ?
        """, (today, limit, offset))
        
        questions = []
        for i, (normalized_question, original_question, answer, source_file, topic, count, created_at) in enumerate(c.fetchall()):
            source_keyword = file_keywords.get(source_file, "") if source_file else ""
            questions.append({
                "id": offset + i + 1,
                "question": original_question,
                "answer": answer,
                "count": count,
                "created_at": created_at,
                "source_file": source_file,
                "source_keyword": source_keyword,
                "topic": topic or "Genel"
            })
        
        # Toplam sayfa sayısını hesapla - unique sorular için
        c.execute("""
        SELECT COUNT(*) as total
        FROM (
            SELECT DISTINCT LOWER(TRIM(question))
            FROM questions 
            WHERE DATE(created_at) = ?
        )
        """, (today,))
        
        total_questions = c.fetchone()[0]
        total_pages = (total_questions + limit - 1) // limit  # Ceiling division
        
        conn.close()
        
        return {
            "questions": questions,
            "total_pages": max(1, total_pages),
            "total_questions": total_questions
        }
        
    except Exception as e:
        print(f"Günlük sorular alınırken hata: {e}")
        return {
            "questions": [],
            "total_pages": 1,
            "total_questions": 0
        }
        
    except Exception as e:
        print(f"Günlük sorular alınırken hata: {e}")
        return {
            "questions": [],
            "total_pages": 1,
            "total_questions": 0
        }

def get_all_questions_paginated(page=1, limit=10):
    """Tüm soruları sayfalayarak al - en çok sorulan sorular için"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        offset = (page - 1) * limit
        
        # Enhanced document data'dan anahtar kelimeleri al
        file_keywords = {}
        try:
            with open("enhanced_document_data.json", "r", encoding="utf-8") as f:
                document_data = json.load(f)
                file_keywords = {item["filename"]: item.get("keyword", "") for item in document_data}
        except Exception as e:
            print(f"Enhanced document data okunamadı: {e}")
        
        # Tüm sorular - aynı soruları grupla (case-insensitive)
        c.execute("""
        SELECT LOWER(TRIM(question)) as normalized_question, 
               question as original_question,
               answer, 
               source_file,
               topic,
               COUNT(*) as count, 
               MIN(created_at) as first_asked
        FROM questions 
        GROUP BY LOWER(TRIM(question))
        ORDER BY count DESC, first_asked DESC
        LIMIT ? OFFSET ?
        """, (limit, offset))
        
        questions = []
        for i, (normalized_question, original_question, answer, source_file, topic, count, created_at) in enumerate(c.fetchall()):
            source_keyword = file_keywords.get(source_file, "") if source_file else ""
            questions.append({
                "id": offset + i + 1,
                "question": original_question,
                "answer": answer,
                "count": count,
                "created_at": created_at,
                "source_file": source_file,
                "source_keyword": source_keyword,
                "topic": topic or "Genel"
            })
        
        # Toplam sayfa sayısını hesapla - unique sorular için
        c.execute("""
        SELECT COUNT(*) as total
        FROM (
            SELECT DISTINCT LOWER(TRIM(question))
            FROM questions 
        )
        """)
        
        total_questions = c.fetchone()[0]
        total_pages = (total_questions + limit - 1) // limit  # Ceiling division
        
        conn.close()
        
        return {
            "questions": questions,
            "total_pages": max(1, total_pages),
            "total_questions": total_questions
        }
        
    except Exception as e:
        print(f"Tüm sorular alınırken hata: {e}")
        return {
            "questions": [],
            "total_pages": 1,
            "total_questions": 0
        }
        
    except Exception as e:
        print(f"Tüm sorular alınırken hata: {e}")
        return {
            "questions": [],
            "total_pages": 1,
            "total_questions": 0
        }

if __name__ == "__main__":
    init_db()
    clear_all_questions()  # Veritabanını temizle
    print("🔄 Veritabanı sıfırlandı ve hazır")