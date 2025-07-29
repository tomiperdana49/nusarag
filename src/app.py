from flask import Flask, jsonify, request, g, render_template, redirect, url_for
from flask_cors import CORS
from service.service import ArticleService, QuestionService, OrganizationService, AskService
from validation.validation import validate_article, validate_question, validate_organizations, validate_question_article_batch

app = Flask(__name__)
CORS(app)

a_service = ArticleService()
q_service = QuestionService()
o_service = OrganizationService()
ak_service = AskService()

@app.route("/", methods=["GET"])
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


if __name__ == "__main__":
    app.run(debug=True)