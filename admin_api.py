from flask import Flask, request, jsonify, g
from functools import wraps
import admin_auth
import question_db
import json


def require_admin_auth(f):
    """Admin authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Authorization header'dan token al
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token gerekli"}), 401

        token = auth_header.split(" ")[1]

        # Token'ı doğrula
        session_result = admin_auth.verify_session(token)
        if not session_result["valid"]:
            return jsonify({"error": session_result["message"]}), 401

        # Admin bilgilerini g'ye ekle
        g.admin_id = session_result["admin_id"]
        g.admin_username = session_result["username"]

        return f(*args, **kwargs)

    return decorated_function


def init_admin_routes(app):
    """Admin rotalarını Flask uygulamasına ekle"""

    @app.route("/admin/login", methods=["POST"])
    def admin_login():
        """Admin giriş"""
        try:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return jsonify({"error": "Kullanıcı adı ve şifre gerekli"}), 400

            # IP ve User-Agent bilgilerini al
            ip_address = request.environ.get("REMOTE_ADDR")
            user_agent = request.headers.get("User-Agent")

            # Giriş yap
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

    @app.route("/admin/logout", methods=["POST"])
    @require_admin_auth
    def admin_logout():
        """Admin çıkış"""
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header:
                token = auth_header.split(" ")[1]

                result = admin_auth.logout_admin(token)
                return jsonify(result)
            else:
                return jsonify({"error": "Token bulunamadı"}), 400

        except Exception as e:
            return jsonify({"error": f"Çıkış hatası: {str(e)}"}), 500

    @app.route("/admin/verify", methods=["GET"])
    @require_admin_auth
    def verify_admin():
        """Admin token doğrulama"""
        return jsonify(
            {"valid": True, "admin_id": g.admin_id, "username": g.admin_username}
        )

    @app.route("/admin/dashboard", methods=["GET"])
    @require_admin_auth
    def admin_dashboard():
        """Admin dashboard verileri"""
        try:
            # Kullanıcı istatistikleri
            user_stats = question_db.get_daily_user_stats()

            # Toplam soru sayısı
            total_questions = question_db.get_total_questions()
            total_unique_questions = question_db.get_total_unique_questions()

            # En çok kullanılan kaynaklar
            top_sources = question_db.get_top_sources(5)

            # En çok sorulan sorular
            top_questions = question_db.get_top_questions_with_topics(5)

            # Aktivite log
            activity_result = admin_auth.get_admin_activity_log(10)
            activity_logs = (
                activity_result["logs"] if activity_result["success"] else []
            )

            return jsonify(
                {
                    "user_stats": user_stats,
                    "question_stats": {
                        "total_questions": total_questions,
                        "unique_questions": total_unique_questions,
                    },
                    "top_sources": top_sources,
                    "top_questions": top_questions,
                    "recent_activity": activity_logs,
                }
            )

        except Exception as e:
            return jsonify({"error": f"Dashboard hatası: {str(e)}"}), 500

    @app.route("/admin/questions/daily", methods=["GET"])
    @require_admin_auth
    def admin_get_daily_questions():
        """Günlük soruları al - Admin Dashboard"""
        try:
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))

            result = question_db.get_daily_questions_paginated(page, limit)
            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Günlük sorular hatası: {str(e)}"}), 500

    @app.route("/admin/questions/all", methods=["GET"])
    @require_admin_auth
    def admin_get_all_questions():
        """Tüm soruları al - Admin Dashboard"""
        try:
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))

            result = question_db.get_all_questions_paginated(page, limit)
            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Tüm sorular hatası: {str(e)}"}), 500

    @app.route("/admin/questions/clear", methods=["POST"])
    @require_admin_auth
    def admin_clear_questions():
        """Soruları temizle - Admin Dashboard"""
        try:
            data = request.get_json()
            period_type = data.get("period", "all")  # 'today' veya 'all'

            affected_rows = question_db.clear_questions_by_period(period_type)

            # Aktiviteyi logla
            admin_auth.log_admin_activity(
                g.admin_id,
                "QUESTIONS_CLEARED",
                f"{period_type} dönemindeki sorular temizlendi - {affected_rows} kayıt",
            )

            return jsonify(
                {
                    "success": True,
                    "message": f"{affected_rows} kayıt temizlendi",
                    "affected_rows": affected_rows,
                }
            )

        except Exception as e:
            return jsonify({"error": f"Temizleme hatası: {str(e)}"}), 500

    @app.route("/admin/users", methods=["GET"])
    @require_admin_auth
    def get_admin_users():
        """Admin kullanıcıları listele"""
        try:
            result = admin_auth.get_admin_users()
            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Kullanıcı listesi hatası: {str(e)}"}), 500

    @app.route("/admin/users", methods=["POST"])
    @require_admin_auth
    def create_admin_user():
        """Yeni admin kullanıcı oluştur"""
        try:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")
            email = data.get("email")
            full_name = data.get("full_name")
            role = data.get("role", "admin")

            if not username or not password:
                return jsonify({"error": "Kullanıcı adı ve şifre gerekli"}), 400

            result = admin_auth.create_admin_user(
                username, password, email, full_name, role
            )

            if result["success"]:
                # Aktiviteyi logla
                admin_auth.log_admin_activity(
                    g.admin_id,
                    "USER_CREATED",
                    f"Yeni admin kullanıcı oluşturuldu: {username}",
                )

            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Kullanıcı oluşturma hatası: {str(e)}"}), 500

    @app.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
    @require_admin_auth
    def deactivate_user(user_id):
        """Kullanıcıyı deaktive et"""
        try:
            result = admin_auth.deactivate_admin_user(g.admin_id, user_id)
            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Deaktivasyon hatası: {str(e)}"}), 500

    @app.route("/admin/password/change", methods=["POST"])
    @require_admin_auth
    def change_password():
        """Şifre değiştir"""
        try:
            data = request.get_json()
            old_password = data.get("old_password")
            new_password = data.get("new_password")

            if not old_password or not new_password:
                return jsonify({"error": "Eski ve yeni şifre gerekli"}), 400

            result = admin_auth.change_admin_password(
                g.admin_id, old_password, new_password
            )
            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Şifre değiştirme hatası: {str(e)}"}), 500

    @app.route("/admin/activity", methods=["GET"])
    @require_admin_auth
    def get_activity_log():
        """Admin aktivite logları"""
        try:
            limit = int(request.args.get("limit", 50))
            result = admin_auth.get_admin_activity_log(limit)
            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Aktivite log hatası: {str(e)}"}), 500

    @app.route("/admin/sources/clean", methods=["POST"])
    @require_admin_auth
    def clean_obsolete_sources():
        """Eski kaynakları temizle"""
        try:
            question_db.clean_obsolete_sources()

            # Aktiviteyi logla
            admin_auth.log_admin_activity(
                g.admin_id, "SOURCES_CLEANED", "Eski kaynaklar temizlendi"
            )

            return jsonify({"success": True, "message": "Eski kaynaklar temizlendi"})

        except Exception as e:
            return jsonify({"error": f"Kaynak temizleme hatası: {str(e)}"}), 500


# Admin veritabanını başlat
def init_admin_db():
    """Admin veritabanını başlat ve varsayılan kullanıcı oluştur"""
    admin_auth.init_admin_db()
    admin_auth.create_default_admin()


if __name__ == "__main__":
    # Test amaçlı çalıştırma
    init_admin_db()
    print("✅ Admin sistemi hazır")
