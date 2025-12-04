import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets
import os

# Admin veritabanı dosyası
ADMIN_DB_PATH = "admin.db"


def hash_password(password):
    """Şifreyi güvenli hash ile şifrele"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"{salt}:{pwd_hash.hex()}"


def verify_password(password, hashed):
    """Şifreyi doğrula"""
    try:
        salt, stored_hash = hashed.split(":")
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return pwd_hash.hex() == stored_hash
    except:
        return False


def generate_session_token():
    """Güvenli session token oluştur"""
    return secrets.token_urlsafe(32)


def init_admin_db():
    """Admin veritabanını başlat"""
    conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
    c = conn.cursor()

    # Admin kullanıcıları tablosu
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'admin',
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        login_attempts INTEGER DEFAULT 0,
        locked_until TIMESTAMP
    )
    """
    )

    # Admin oturum tablosu
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS admin_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        session_token TEXT UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_agent TEXT,
        ip_address TEXT,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY(admin_id) REFERENCES admin_users(id)
    )
    """
    )

    # Admin aktivite logu
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS admin_activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(admin_id) REFERENCES admin_users(id)
    )
    """
    )

    conn.commit()
    conn.close()


def create_admin_user(username, password, email=None, full_name=None, role="admin"):
    """Yeni admin kullanıcı oluştur"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        # Kullanıcı adı kontrolü
        c.execute("SELECT id FROM admin_users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return {"success": False, "message": "Bu kullanıcı adı zaten mevcut"}

        # Şifreyi hash'le
        password_hash = hash_password(password)

        # Kullanıcıyı ekle
        c.execute(
            """
        INSERT INTO admin_users (username, password_hash, email, full_name, role)
        VALUES (?, ?, ?, ?, ?)
        """,
            (username, password_hash, email, full_name, role),
        )

        admin_id = c.lastrowid

        # Aktiviteyi logla
        log_admin_activity(
            admin_id, "USER_CREATED", f"Admin kullanıcı oluşturuldu: {username}"
        )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": "Admin kullanıcı başarıyla oluşturuldu",
            "admin_id": admin_id,
        }

    except Exception as e:
        return {"success": False, "message": f"Kullanıcı oluşturma hatası: {str(e)}"}


def authenticate_admin(username, password, ip_address=None, user_agent=None):
    """Admin kullanıcı doğrulama"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        # Kullanıcıyı bul
        c.execute(
            """
        SELECT id, username, password_hash, is_active, login_attempts, locked_until
        FROM admin_users WHERE username = ?
        """,
            (username,),
        )

        user = c.fetchone()
        if not user:
            conn.close()
            return {"success": False, "message": "Kullanıcı bulunamadı"}

        admin_id, username, password_hash, is_active, login_attempts, locked_until = (
            user
        )

        # Hesap aktif mi?
        if not is_active:
            conn.close()
            return {"success": False, "message": "Hesap devre dışı"}

        # Hesap kilitli mi?
        if locked_until:
            lock_time = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
            if datetime.utcnow() < lock_time:
                conn.close()
                return {"success": False, "message": "Hesap geçici olarak kilitli"}

        # Şifre doğrulama
        if not verify_password(password, password_hash):
            # Başarısız giriş denemesi
            login_attempts += 1

            # 5 başarısız denemeden sonra 30 dakika kilitle
            if login_attempts >= 5:
                lock_until = datetime.utcnow() + timedelta(minutes=30)
                c.execute(
                    """
                UPDATE admin_users
                SET login_attempts = ?, locked_until = ?
                WHERE id = ?
                """,
                    (login_attempts, lock_until.isoformat(), admin_id),
                )

                log_admin_activity(
                    admin_id,
                    "ACCOUNT_LOCKED",
                    f"Hesap kilitlendi - çok fazla başarısız giriş",
                )
            else:
                c.execute(
                    """
                UPDATE admin_users
                SET login_attempts = ?
                WHERE id = ?
                """,
                    (login_attempts, admin_id),
                )

            log_admin_activity(
                admin_id,
                "LOGIN_FAILED",
                f"Başarısız giriş denemesi",
                ip_address,
                user_agent,
            )

            conn.commit()
            conn.close()
            return {"success": False, "message": "Hatalı şifre"}

        # Başarılı giriş
        # Session token oluştur
        session_token = generate_session_token()
        expires_at = datetime.utcnow() + timedelta(hours=8)  # 8 saat geçerli

        # Session'ı kaydet
        c.execute(
            """
        INSERT INTO admin_sessions (admin_id, session_token, expires_at, user_agent, ip_address)
        VALUES (?, ?, ?, ?, ?)
        """,
            (admin_id, session_token, expires_at.isoformat(), user_agent, ip_address),
        )

        # Kullanıcı bilgilerini güncelle
        c.execute(
            """
        UPDATE admin_users
        SET last_login = CURRENT_TIMESTAMP, login_attempts = 0, locked_until = NULL
        WHERE id = ?
        """,
            (admin_id,),
        )

        # Aktiviteyi logla
        log_admin_activity(
            admin_id, "LOGIN_SUCCESS", "Başarılı giriş", ip_address, user_agent
        )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": "Giriş başarılı",
            "session_token": session_token,
            "admin_id": admin_id,
            "username": username,
            "expires_at": expires_at.isoformat(),
        }

    except Exception as e:
        return {"success": False, "message": f"Giriş hatası: {str(e)}"}


def verify_session(session_token):
    """Session token doğrulama"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        # Session'ı kontrol et
        c.execute(
            """
        SELECT s.admin_id, s.expires_at, u.username, u.is_active
        FROM admin_sessions s
        JOIN admin_users u ON s.admin_id = u.id
        WHERE s.session_token = ? AND s.is_active = 1
        """,
            (session_token,),
        )

        session = c.fetchone()
        if not session:
            conn.close()
            return {"valid": False, "message": "Geçersiz session"}

        admin_id, expires_at, username, is_active = session

        # Kullanıcı aktif mi?
        if not is_active:
            conn.close()
            return {"valid": False, "message": "Hesap devre dışı"}

        # Session süresi dolmuş mu?
        expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.utcnow() > expiry_time:
            # Süresi dolmuş session'ı deaktive et
            c.execute(
                "UPDATE admin_sessions SET is_active = 0 WHERE session_token = ?",
                (session_token,),
            )
            conn.commit()
            conn.close()
            return {"valid": False, "message": "Session süresi dolmuş"}

        conn.close()

        return {"valid": True, "admin_id": admin_id, "username": username}

    except Exception as e:
        return {"valid": False, "message": f"Session doğrulama hatası: {str(e)}"}


def logout_admin(session_token):
    """Admin çıkış"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        # Session'ı bul ve admin_id'yi al
        c.execute(
            "SELECT admin_id FROM admin_sessions WHERE session_token = ?",
            (session_token,),
        )
        result = c.fetchone()

        if result:
            admin_id = result[0]

            # Session'ı deaktive et
            c.execute(
                "UPDATE admin_sessions SET is_active = 0 WHERE session_token = ?",
                (session_token,),
            )

            # Aktiviteyi logla
            log_admin_activity(admin_id, "LOGOUT", "Çıkış yapıldı")

            conn.commit()

        conn.close()
        return {"success": True, "message": "Çıkış başarılı"}

    except Exception as e:
        return {"success": False, "message": f"Çıkış hatası: {str(e)}"}


def log_admin_activity(
    admin_id, action, details=None, ip_address=None, user_agent=None
):
    """Admin aktivitesini logla"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        c.execute(
            """
        INSERT INTO admin_activity_log (admin_id, action, details, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?)
        """,
            (admin_id, action, details, ip_address, user_agent),
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Aktivite loglama hatası: {e}")


def get_admin_users():
    """Tüm admin kullanıcıları listele"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        c.execute(
            """
        SELECT id, username, email, full_name, role, is_active, created_at, last_login
        FROM admin_users
        ORDER BY created_at DESC
        """
        )

        users = []
        for row in c.fetchall():
            users.append(
                {
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "full_name": row[3],
                    "role": row[4],
                    "is_active": bool(row[5]),
                    "created_at": row[6],
                    "last_login": row[7],
                }
            )

        conn.close()
        return {"success": True, "users": users}

    except Exception as e:
        return {"success": False, "message": f"Kullanıcı listesi hatası: {str(e)}"}


def get_admin_activity_log(limit=50):
    """Admin aktivite loglarını al"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        c.execute(
            """
        SELECT al.id, al.admin_id, u.username, al.action, al.details,
               al.ip_address, al.created_at
        FROM admin_activity_log al
        LEFT JOIN admin_users u ON al.admin_id = u.id
        ORDER BY al.created_at DESC
        LIMIT ?
        """,
            (limit,),
        )

        logs = []
        for row in c.fetchall():
            logs.append(
                {
                    "id": row[0],
                    "admin_id": row[1],
                    "username": row[2],
                    "action": row[3],
                    "details": row[4],
                    "ip_address": row[5],
                    "created_at": row[6],
                }
            )

        conn.close()
        return {"success": True, "logs": logs}

    except Exception as e:
        return {"success": False, "message": f"Aktivite log hatası: {str(e)}"}


def change_admin_password(admin_id, old_password, new_password):
    """Admin şifresi değiştir"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        # Mevcut şifreyi kontrol et
        c.execute("SELECT password_hash FROM admin_users WHERE id = ?", (admin_id,))
        result = c.fetchone()

        if not result:
            conn.close()
            return {"success": False, "message": "Kullanıcı bulunamadı"}

        current_hash = result[0]

        if not verify_password(old_password, current_hash):
            conn.close()
            return {"success": False, "message": "Mevcut şifre hatalı"}

        # Yeni şifreyi hash'le ve güncelle
        new_hash = hash_password(new_password)
        c.execute(
            "UPDATE admin_users SET password_hash = ? WHERE id = ?",
            (new_hash, admin_id),
        )

        # Aktiviteyi logla
        log_admin_activity(admin_id, "PASSWORD_CHANGED", "Şifre değiştirildi")

        conn.commit()
        conn.close()

        return {"success": True, "message": "Şifre başarıyla değiştirildi"}

    except Exception as e:
        return {"success": False, "message": f"Şifre değiştirme hatası: {str(e)}"}


def deactivate_admin_user(admin_id, target_user_id):
    """Admin kullanıcısını deaktive et"""
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH, timeout=60.0, check_same_thread=False)
        c = conn.cursor()

        # Hedef kullanıcıyı deaktive et
        c.execute(
            "UPDATE admin_users SET is_active = 0 WHERE id = ?", (target_user_id,)
        )

        # Aktif session'ları sonlandır
        c.execute(
            "UPDATE admin_sessions SET is_active = 0 WHERE admin_id = ?",
            (target_user_id,),
        )

        # Aktiviteyi logla
        log_admin_activity(
            admin_id, "USER_DEACTIVATED", f"Kullanıcı deaktive edildi: {target_user_id}"
        )

        conn.commit()
        conn.close()

        return {"success": True, "message": "Kullanıcı deaktive edildi"}

    except Exception as e:
        return {"success": False, "message": f"Deaktivasyon hatası: {str(e)}"}


def create_default_admin():
    """Varsayılan admin kullanıcı oluştur"""
    default_username = "admin"
    default_password = "admin123"

    result = create_admin_user(
        username=default_username,
        password=default_password,
        email="admin@localhost",
        full_name="Sistem Yöneticisi",
        role="super_admin",
    )

    if result["success"]:
        print(f"✅ Varsayılan admin oluşturuldu:")
        print(f"   Kullanıcı adı: {default_username}")
        print(f"   Şifre: {default_password}")
        print(f"   ⚠️  Güvenlik için şifreyi değiştirin!")
    else:
        if "zaten mevcut" in result["message"]:
            print(f"ℹ️  Varsayılan admin zaten mevcut")
        else:
            print(f"❌ Varsayılan admin oluşturulamadı: {result['message']}")


if __name__ == "__main__":
    # Veritabanını başlat
    init_admin_db()
    print("✅ Admin veritabanı başlatıldı")

    # Varsayılan admin oluştur
    create_default_admin()
