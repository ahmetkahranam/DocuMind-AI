# 🤖 DocuMind-AI

[English](#english) | [Türkçe](#turkish)

---

## English

**DocuMind-AI** is an intelligent document Q&A system that runs completely offline using RAG (Retrieval-Augmented Generation) technology.

### 🌟 Features

- 📄 **Multi-Format Support**: Upload PDF, DOCX, TXT, MD files
- 🤖 **Local AI Models**: Runs completely offline (Ollama + SentenceTransformers)
- 🔍 **Smart Search**: Hybrid retrieval with semantic and keyword-based search
- 💬 **Intelligent Chat**: Ask questions about your documents in natural language
- 🔐 **Admin Panel**: Document management, statistics, and user administration
- 📊 **Analytics**: Question history and document usage analytics
- 🎨 **Modern UI**: Responsive design with React + Material-UI

### 🛠️ Tech Stack

**Backend**
- Flask (Python)
- Ollama (DeepSeek-R1 LLM)
- SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2)
- ChromaDB (Vector Database)
- SQLite

**Frontend**
- React 19 + TypeScript
- Material-UI (MUI)
- React Router v7
- Axios

### 📋 Requirements

- Python 3.8+
- Node.js 16+
- Ollama (with DeepSeek-R1 model)
- 8GB RAM (minimum)

### 🚀 Installation

#### 1. Install Ollama
```bash
# Download from: https://ollama.ai/download
# Pull DeepSeek-R1 model
ollama pull deepseek-r1:latest
```

#### 2. Clone Repository
```bash
git clone https://github.com/ahmetkahranam/DocuMind-AI.git
cd DocuMind-AI
```

#### 3. Backend Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize databases
python -c "from admin_auth import init_admin_db, create_default_admin; from question_db import init_db; init_admin_db(); create_default_admin(); init_db()"
```

#### 4. Frontend Setup
```bash
cd frontend
npm install
```

### 🎮 Running

**Backend:**
```bash
python api.py
```
Runs on: http://localhost:5001

**Frontend:**
```bash
cd frontend
npm start
```
Opens at: http://localhost:3000

### 🔑 Default Admin Credentials

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Important**: Change your password after first login!

### 📖 Usage

1. **Admin Login**: Go to http://localhost:3000/admin/login
2. **Upload Documents**: Click "Documents" tab → "Select File" → Add keyword → Upload
3. **Chat**: Ask questions about your documents on the main page
4. **Statistics**: View question history and document analytics in admin panel

### 📁 Project Structure

```
DocuMind-AI/
├── api.py                 # Main Flask application
├── rag_chatbot.py        # RAG chatbot logic
├── embedder.py           # Embedding operations
├── chroma.py             # ChromaDB management
├── hybrid_retriever.py   # Hybrid retrieval system
├── admin_auth.py         # Admin authentication
├── question_db.py        # Question database
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── frontend/             # React frontend
├── chroma/              # ChromaDB vector database
├── docs/                # Uploaded documents
└── uploads/             # Temporary upload folder
```

### 🔧 Configuration

Edit `config.py` for important settings:

```python
LLM_MODEL = "deepseek-r1:latest"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_N_RESULTS = 10
SIMILARITY_THRESHOLD = 0.01
MAX_CONTEXT_LENGTH = 16000
```

### 🐛 Troubleshooting

**Ollama Connection Error:**
```bash
ollama serve
```

**Port Already in Use:**
Change ports in `api.py` (5001) or `frontend/package.json` (proxy setting)

### 📝 License

MIT License

### 👨‍💻 Developer

**Ahmet Kahraman**
- GitHub: [@ahmetkahranam](https://github.com/ahmetkahranam)

---

## Turkish

**DocuMind-AI**, yüklenen belgeler üzerinde akıllı soru-cevap yapabilen, tamamen yerel çalışan bir RAG (Retrieval-Augmented Generation) sistemidir.

### 🌟 Özellikler

- 📄 **Çoklu Doküman Desteği**: PDF, DOCX, TXT, MD formatlarında belge yükleyin
- 🤖 **Yerel AI Modelleri**: Tamamen offline çalışır (Ollama + SentenceTransformers)
- 🔍 **Akıllı Arama**: Semantic ve keyword-based hibrit retrieval
- 💬 **Akıllı Sohbet**: Yüklenen belgeler üzerinden doğal dil ile soru sorun
- 🔐 **Admin Paneli**: Belge yönetimi, istatistikler ve kullanıcı yönetimi
- 📊 **İstatistikler**: Soru geçmişi, belge kullanım analizi
- 🎨 **Modern Arayüz**: React + Material-UI ile responsive tasarım

### 🛠️ Teknoloji Stack

**Backend**
- Flask (Python)
- Ollama (DeepSeek-R1 LLM)
- SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2)
- ChromaDB (Vektör Veritabanı)
- SQLite

**Frontend**
- React 19 + TypeScript
- Material-UI (MUI)
- React Router v7
- Axios

### 📋 Gereksinimler

- Python 3.8+
- Node.js 16+
- Ollama (DeepSeek-R1 modeli ile)
- 8GB RAM (minimum)

### 🚀 Kurulum

#### 1. Ollama Kurulumu
```bash
# İndirin: https://ollama.ai/download
# DeepSeek-R1 modelini çekin
ollama pull deepseek-r1:latest
```

#### 2. Projeyi Klonlayın
```bash
git clone https://github.com/ahmetkahranam/DocuMind-AI.git
cd DocuMind-AI
```

#### 3. Backend Kurulumu
```bash
# Sanal ortam oluşturun
python -m venv .venv

# Aktifleştirin (Windows)
.venv\Scripts\activate

# Aktifleştirin (Linux/Mac)
source .venv/bin/activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Veritabanlarını başlatın
python -c "from admin_auth import init_admin_db, create_default_admin; from question_db import init_db; init_admin_db(); create_default_admin(); init_db()"
```

#### 4. Frontend Kurulumu
```bash
cd frontend
npm install
```

### 🎮 Çalıştırma

**Backend:**
```bash
python api.py
```
Adres: http://localhost:5001

**Frontend:**
```bash
cd frontend
npm start
```
Adres: http://localhost:3000

### 🔑 Varsayılan Admin Bilgileri

- **Kullanıcı Adı**: `admin`
- **Şifre**: `admin123`

⚠️ **Önemli**: İlk girişten sonra mutlaka şifrenizi değiştirin!

### 📖 Kullanım

1. **Admin Girişi**: http://localhost:3000/admin/login adresine gidin
2. **Belge Yükleme**: "Dokümanlar" sekmesi → "Dosya Seç" → Anahtar kelime ekle → Yükle
3. **Sohbet**: Ana sayfada belgeleriniz hakkında sorular sorun
4. **İstatistikler**: Admin panelde soru geçmişi ve belge analizlerini görün

### 📁 Proje Yapısı

```
DocuMind-AI/
├── api.py                 # Ana Flask uygulaması
├── rag_chatbot.py        # RAG chatbot mantığı
├── embedder.py           # Embedding işlemleri
├── chroma.py             # ChromaDB yönetimi
├── hybrid_retriever.py   # Hibrit retrieval sistemi
├── admin_auth.py         # Admin yetkilendirme
├── question_db.py        # Soru veritabanı
├── config.py             # Konfigürasyon ayarları
├── requirements.txt      # Python bağımlılıkları
├── frontend/             # React frontend
├── chroma/              # ChromaDB vektör veritabanı
├── docs/                # Yüklenen belgeler
└── uploads/             # Geçici yükleme klasörü
```

### 🔧 Konfigürasyon

`config.py` dosyasından önemli ayarları değiştirebilirsiniz:

```python
LLM_MODEL = "deepseek-r1:latest"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_N_RESULTS = 10
SIMILARITY_THRESHOLD = 0.01
MAX_CONTEXT_LENGTH = 16000
```

### 🐛 Sorun Giderme

**Ollama Bağlantı Hatası:**
```bash
ollama serve
```

**Port Kullanımda:**
`api.py` (5001) veya `frontend/package.json` (proxy ayarı) dosyalarından portları değiştirin

### 📝 Lisans

MIT License

### 👨‍💻 Geliştirici

**Ahmet Kahraman**
- GitHub: [@ahmetkahranam](https://github.com/ahmetkahranam)

---

⭐ **Bu projeyi beğendiyseniz yıldız vermeyi unutmayın!**

**Not**: Bu sistem tamamen offline çalışır ve herhangi bir harici API'ye bağımlı değildir.
