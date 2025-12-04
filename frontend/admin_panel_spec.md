
# 📊 Admin Panel Özellikleri – Üniversite Q/A Chatbot

Bu belge, üniversite için geliştirilen LLM + RAG tabanlı soru-cevap (Q/A) chatbot sistemi için tasarlanan **basit admin paneli** işlevlerini tanımlar.

## 🎯 Amaç

Yönetici paneli, sistem yöneticilerinin chatbot kullanım verilerini analiz etmesini ve bilgi kaynaklarını (belgeleri) kolayca yönetmesini sağlar.

---

## 1. 📈 Analiz Dashboard

### Amaç:
Sistemin kullanım istatistiklerini görsel ve sayısal olarak sunmak.

### Fonksiyonlar:
- ✅ Toplam Soru Sayısı (LLM'e gelen)
- 📆 Günlük / haftalık sorgu sayısı (grafiksel)
- ❓ En çok sorulan ilk 5 soru
- 📚 En çok sorgulanan belgeler (RAG verileri)
- 📊 Hatalı veya cevapsız kalan cevap oranı (%)

### Görsel Bileşenler (Örnek):
- Line Chart → Tarih bazlı soru sayısı
- Pie Chart → Cevap başarı oranları
- Bar Chart → En çok çağrılan belgeler
- Sayı kutuları → Toplam belge / toplam soru sayısı

---

## 2. 📁 Belge Yönetimi

### Amaç:
Chatbot'un bilgi tabanını oluşturan belgeleri (PDF, DOCX, TXT) yüklemek, düzenlemek ve işlemek.

### Fonksiyonlar:
- 📤 Yeni belge yükleme (tekli veya çoklu)
- 📃 Belge listesi (isim, tarih, durum)
- 🔄 Belgeyi işleme sok (embedding başlatma)
- ❌ Belge silme / güncelleme

### Tabloda Görünen Bilgiler:
| Sütun              | Açıklama                           |
|--------------------|------------------------------------|
| Belge Adı          | `akademik_takvim_2025.pdf`         |
| Yüklenme Tarihi    | `03.07.2025`                       |
| Durum              | ✅ İşlendi / 🔄 İşleniyor / ❌ Hatalı |
| İşlem              | [Sil] [İşle] [Detay]                |

---

## 📦 Önerilen Teknolojiler

| Katman      | Teknoloji                  |
|-------------|----------------------------|
| Frontend    | React.js + Chart.js        |
| Backend     | Express.js (Node.js)       |
| Veritabanı  | SQLite veya PostgreSQL     |
| Dosya Yükleme | Multer (Node.js için)     |
| Embedding   | SentenceTransformers, Faiss, vb. |

---

## 🔐 Notlar

- Panel erişimi yalnızca yetkili yöneticilere açık olmalıdır.
- Belgeler yüklendikten sonra arka planda embedding başlatılabilir veya elle tetiklenebilir.
- Dashboard verileri günlük olarak güncellenebilir veya canlı veri çekilebilir.

---

## ✍️ Yazar: İshak Duran  
_Bilgisayar Mühendisliği Öğrencisi, LLM-RAG Geliştirici_
