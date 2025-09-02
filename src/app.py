from flask import Flask, jsonify, request, g, render_template, redirect, url_for
from flask_cors import CORS
from service.service import ArticleService, QuestionService, OrganizationService, AskService, LogService, webHook
from validation.validation import validate_article, validate_question, validate_organizations, validate_question_article_batch, validate_article_batch, validate_question_batch
from validation.authentication import tokenService,require_token
import os, jwt
import requests
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

a_service = ArticleService()
q_service = QuestionService()
o_service = OrganizationService()
ak_service = AskService()
l_service = LogService()
h = webHook()
t_service = tokenService()

#=============================#
# TOKENISASI
#=============================#
@app.route("/get-token", methods=["POST"])
def get_token():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        return jsonify({"error": "Invalid auth"}), 401
    payload = t_service.getToken(auth)
    if not payload or "error" in payload:
        return payload
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 3600})

#=============================#
# Autogen Token
#=============================#
@app.route("/request-access-nusa", methods=["POST"])
def get_access():
    body = request.get_json();
    if body is None:
        return jsonify({"error": "Data is none"}), 404
    check = t_service.checkUsers(body)
    if check == False:
        return jsonify({"error": "Your email is invalid"}), 401

    resp = requests.post(
       os.getenv("TOKEN_API"),
        auth=(os.getenv("NUSA_ID"), os.getenv("NUSA_SECRET"))
    )
    if resp.status_code != 200:
        return jsonify({"error": "cannot get token"}), 500
    token = resp.json()["access_token"]
    method = body.get("method", "POST").upper()
    url_target = body.get("url_target")
    payload = body.get("payload")
    if method == "POST":
        api_resp = requests.post(
            url_target,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    else:
       api_resp = requests.get(
            url_target,
            headers={"Authorization": f"Bearer {token}"},
            json=payload, 
       )

    if "application/json" in api_resp.headers.get("Content-Type", ""):
        result = api_resp.json()
    else:
        result = api_resp.text
    return jsonify(result), api_resp.status_code

@app.route("/request-access-users", methods=["POST"])
def get_access_user():
    body = request.get_json();
    if body is None:
        return jsonify({"error": "Data is none"}), 404
    resp = requests.post(
       os.getenv("TOKEN_API"),
        auth=(os.getenv("USERS_ID"), os.getenv("USERS_SECRET"))
    )
    if resp.status_code != 200:
        return jsonify({"error": "cannot get token"}), 500
    token = resp.json()["access_token"]
    method = body.get("method", "POST").upper()
    url_target = body.get("url_target")
    payload = body.get("payload")
    if method == "POST":
        api_resp = requests.post(
            url_target,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    else:
       api_resp = requests.get(
            url_target,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
       )

    if "application/json" in api_resp.headers.get("Content-Type", ""):
        result = api_resp.json()
    else:
        result = api_resp.text
    return jsonify(result), api_resp.status_code

@app.route("/", methods=["GET"])
def main():
    return jsonify({
        "status": "OK",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "service": "Seluruh aktivitas dikelola oleh Flask"
    })
@app.route("/test", methods=["POST"])
@require_token(role="private")
def testing():
    body = request.get_json();
    return jsonify({
        "data": body,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "service": "Seluruh aktivitas dikelola oleh Flask"
    })

@app.route("/test-public", methods=["POST"])
@require_token(role="public")
def testing_public():
    body = request.get_json();
    return jsonify({
        "payload": body.get("payload", {}),
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "service": "Seluruh aktivitas dikelola oleh Flask"
    })

@app.route("/articles", methods=["GET"])
@require_token(role="private")
def get_articles():
    try:
        articles = a_service.get_all_articles()
        return jsonify({"success": True, "data": articles})
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mengambil data artikel", "error": str(e)}), 500

@app.route("/articles", methods=["POST"])
@require_token(role="private")
@validate_article
def create_article():
    try:
        body = request.get_json()
        new_article = a_service.create_article(body)
        return jsonify({"success": True, "message": "Artikel berhasil ditambahkan", "data": new_article}), 201
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal menambahkan artikel", "error": str(e)}), 500

@app.route("/articles/<int:id>", methods=["GET"])
@require_token(role="private")
def get_article_by_id(id):
    try:
        article = a_service.get_article_by_id(id)
        if article:
            return jsonify({"success": True, "data": article})
        else:
            return jsonify({"success": False, "message": "Artikel tidak ditemukan"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mengambil data artikel", "error": str(e)}), 500

# Route menuju question
@app.route("/questions", methods=["GET"])
@require_token(role="private")
def get_all_questions():
    try:
        question = q_service.get_all_question()
        return jsonify({"success": True, "data": question})
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mengambil data question", "error": str(e)}), 500
    
@app.route("/questions", methods=["POST"], endpoint="create_questions")
@require_token(role="private")
@validate_question
def create_questions():
    try:
        body = g.question_data 
        new_question = q_service.create_questions(body)
        return jsonify({"success": True, "message": "Pertanyaan berhasil ditambahkan", "data": new_question}), 201
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal menambahkan pertanyaan", "error": str(e)}), 500
    
@app.route("/question-articles", methods=["POST"])
@require_token(role="private")
@validate_question_article_batch
def create_question_articles_batch():
    data = g.question_article_batch_data
    try:
        result = q_service.attach_articles_to_questions_batch(data)
        
        if result.get("success") is False:
            return jsonify(result), 400  # Bad request for invalid ID
        
        return jsonify({
            "success": True,
            "message": f"{len(data)} relasi berhasil dibuat"
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan saat menyimpan data.",
            "error": str(e)
        }), 500

@app.route("/questions/<int:id>", methods=["GET"])
@require_token(role="private")
def get_questions_by_id(id):
    try:
        questions = q_service.get_questions_by_id(id)
        if questions:
            return jsonify({"success": True, "data": questions})
        else:
            return jsonify({"success": False, "message": "Questions tidak ditemukan"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mengambil data questions", "error": str(e)}), 500
 
@app.route("/organizations", methods=["GET"])
@require_token(role="private")
def get_organization():
    try:
        organizations = o_service.get_organizations()
        return jsonify({"success": True, "data": organizations})
    except Exception as e :
        return jsonify({"success": False, "message": "Gagal mengambil data organisasi...", "error": str(e)}), 500
    
@app.route("/organizations/<int:id>", methods=["GET"])
@require_token(role="private")
def get_organizations_by_id(id):
    try:
        organizations = o_service.get_organizations_by_id(id)
        if organizations:
            return jsonify({"success": True, "data": organizations})
        else:
            return jsonify({"success": False, "message": "Questions tidak ditemukan"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mengambil data questions", "error": str(e)}), 500

@app.route("/organizations", methods=["POST"])
@require_token(role="private")
@validate_organizations
def create_organizations():
    try:
        body = request.get_json()
        new_organization = o_service.create_organizations(body) 
        return jsonify({"success": True, "message": "Organisasi berhasil ditambahkan", "data": new_organization}), 201
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal menambahkan organisasi", "error": str(e)}), 500


@app.route("/ask", methods={"POST"})
def ask():
    try:
        body = request.get_json()
        asking = ak_service.asking(body) 
        return jsonify({"success": True, "data": asking})
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mendapatkan jawaban", "error": str(e)}), 500

@app.route("/questions-batch", methods=["POST"])
@require_token(role="private")
@validate_question_batch
def create_questions_batch():
    data = g.question_batch_data
    try:
        result = q_service.create_question_batch(data)

        if result.get("success") is False:
            return jsonify(result), 400

        return jsonify({
            "success": True,
            "message": f"{len(data)} questions successfully processed",
            "data": result.get("data", [])
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred while processing question batch.",
            "error": str(e)
        }), 500

# Endpoint: /articles
@app.route("/articles-batch", methods=["POST"])
@require_token(role="private")
@validate_article_batch
def create_articles_batch_v():
    data = g.article_batch_data
    try:
        result = a_service.create_article_batch(data)

        if result.get("success") is False:
            return jsonify(result), 400

        return jsonify({
            "success": True,
            "message": f"{len(data)} articles successfully processed",
            "data": result.get("data", [])
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred while processing article batch.",
            "error": str(e)
        }), 500

@app.route("/log", methods=["GET"])
@require_token(role="private")
def getLog():
    data = l_service.get_Log()
    return jsonify(data)

@app.route("/get-article", methods=['GET'])
@require_token(role="private")
def getArticleId():
    data = a_service.getArticle_Id()
    return jsonify(data)

@app.route("/listen-hook", methods=['POST'])
@require_token(role="private")
def listener():
    payload = request.data.decode("utf-8")
    save = h.setListenerHook(payload)
    return "ok", 200

@app.route("/delete-article", methods=['POST'])
@require_token(role="private")
def clearArticle():
    articleId = request.get_json();
    if articleId is None:
        return "Id is None", 404
    deleteArticel = a_service.deleteArticle(articleId);
    if deleteArticel is not None:
        return"ok", 200

if __name__ == "__main__":
    app.run(debug=True)