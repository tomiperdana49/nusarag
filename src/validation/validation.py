from flask import request, jsonify, g
from connection.connection import get_connection

def validate_article(func):
    def wrapper(*args, **kwargs):
        data = request.get_json()

        # Cek jika JSON tidak valid atau kosong
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body tidak boleh kosong atau harus berupa JSON valid"
            }), 400

        # Field wajib
        required = ['id','title', 'content', 'author', 'organization_id', 'status', 'created_by']

        # Jika updated_by tidak dikirim, kita isi default sama dengan created_by
        if 'updated_by' not in data and 'created_by' in data:
            data['updated_by'] = data['created_by']

        # Validasi field wajib
        missing = [field for field in required if field not in data]
        if missing:
            return jsonify({
                "success": False,
                "message": f"Field {', '.join(missing)} wajib diisi"
            }), 400
        

        # Simpan ke flask.g agar bisa diakses di fungsi route
        g.article_data = data
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper
 

def validate_question(func):
    def wrapper(*args, **kwargs):
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body tidak boleh kosong atau harus berupa JSON valid"
            }), 400

        required = ["id", "question", "organization_id", "created_by", "status"]

        missing = [field for field in required if field not in data]
        if missing:
            return jsonify({
                "success": False,
                "message": f"Field {', '.join(missing)} wajib diisi"
            }), 400

        # Tambahkan updated_by jika tidak ada
        if 'created_by' in data and 'updated_by' not in data:
            data['updated_by'] = data['created_by']

        # Optional: validasi jika article_id disertakan
        if 'article_id' in data:
            if not isinstance(data['article_id'], int):
                return jsonify({
                    "success": False,
                    "message": "Field 'article_id' harus berupa integer jika diberikan"
                }), 400

        g.question_data = data
        return func(*args, **kwargs)

    return wrapper

def validate_question_article(func):
    def wrapper(*args, **kwargs):
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body tidak boleh kosong atau harus berupa JSON valid"
            }), 400

        required = ["question_id", "article_id"]
        missing = [field for field in required if field not in data]
        if missing:
            return jsonify({
                "success": False,
                "message": f"Field {', '.join(missing)} wajib diisi"
            }), 400

        if not isinstance(data["question_id"], int) or not isinstance(data["article_id"], int):
            return jsonify({
                "success": False,
                "message": "question_id dan article_id harus berupa integer"
            }), 400

        g.question_article_data = data
        return func(*args, **kwargs)

    return wrapper

def validate_organizations(func):
    def wrapper(*args, **kwargs):
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body tidak boleh kosong atau harus berupa JSON valid"
            }), 400

        required = ["name"]
        missing = [field for field in required if field not in data]
        if missing:
            return jsonify({
                "success": False,
                "message": f"Field {', '.join(missing)} wajib diisi"
            }), 400

        conn = get_connection()
        cur = conn.cursor()

        # Perhatikan tuple parameter
        query = "SELECT name FROM organizations WHERE name ILIKE %s"
        cur.execute(query, (data["name"],))
        if cur.fetchone():
            return jsonify({
                "success": False,
                "message": "Nama organisasi sudah terdaftar"
            }), 400

        g.organization_data = data
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper

