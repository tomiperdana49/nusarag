from flask import Flask, jsonify, request, g, render_template, redirect, url_for
from flask_cors import CORS
from service.service import ArticleService, QuestionService, OrganizationService, AskService, LogService, webHook
from validation.validation import validate_article, validate_question, validate_organizations, validate_question_article_batch, validate_article_batch, validate_question_batch
from validation.authentication import tokenService,require_token
import os, jwt
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

@app.route("/getToken", methods=["POST"])
def get_token():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        return jsonify({"error": "Invalid auth"}), 401
    payload = t_service.getToken(auth)
    if not payload or "error" in payload:
        return payload
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 3600})

@app.route("/", methods=["GET"])
@require_token(role="public")
def main():
    return jsonify({
        "status": "OK",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "service": "Seluruh aktivitas dikelola oleh Flask"
    })

@app.route("/articles", methods=["GET"])
def get_articles():
    try:
        articles = a_service.get_all_articles()
        return jsonify({"success": True, "data": articles})
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mengambil data artikel", "error": str(e)}), 500

@app.route("/articles", methods=["POST"])
@validate_article
def create_article():
    try:
        body = request.get_json()
        new_article = a_service.create_article(body)
        return jsonify({"success": True, "message": "Artikel berhasil ditambahkan", "data": new_article}), 201
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal menambahkan artikel", "error": str(e)}), 500

@app.route("/articles/<int:id>", methods=["GET"])
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
def get_all_questions():
    try:
        question = q_service.get_all_question()
        return jsonify({"success": True, "data": question})
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal mengambil data question", "error": str(e)}), 500
    
@app.route("/questions", methods=["POST"], endpoint="create_questions")
@validate_question
def create_questions():
    try:
        body = g.question_data 
        new_question = q_service.create_questions(body)
        return jsonify({"success": True, "message": "Pertanyaan berhasil ditambahkan", "data": new_question}), 201
    except Exception as e:
        return jsonify({"success": False, "message": "Gagal menambahkan pertanyaan", "error": str(e)}), 500
    
@app.route("/question-articles", methods=["POST"])
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
def get_organization():
    try:
        organizations = o_service.get_organizations()
        return jsonify({"success": True, "data": organizations})
    except Exception as e :
        return jsonify({"success": False, "message": "Gagal mengambil data organisasi...", "error": str(e)}), 500
    
@app.route("/organizations/<int:id>", methods=["GET"])
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

@app.route("/questionsbatch", methods=["POST"])
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
@app.route("/articlesbatch", methods=["POST"])
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
def getLog():
    data = l_service.get_Log()
    return jsonify(data)

@app.route("/getArticle", methods=['GET'])
def getArticleId():
    data = a_service.getArticle_Id()
    return jsonify(data)

@app.route("/listenHook", methods=['POST'])
def listener():
    payload = request.data.decode("utf-8")
    save = h.setListenerHook(payload)
    return "ok", 200

@app.route("/deleteArticle", methods=['POST'])
def clearArticle():
    articleId = request.get_json();
    if articleId is None:
        return "Id is None", 404
    deleteArticel = a_service.deleteArticle(articleId);
    if deleteArticel is not None:
        return"ok", 200

if __name__ == "__main__":
    app.run(debug=True)