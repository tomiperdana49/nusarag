from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from connection.connection import get_connection
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def find_question_only(session_id):
    conn = get_connection()
    cur = conn.cursor()

    query= """
            SELECT 
                question
            FROM 
                log
            WHERE 
                session_id = %s
            LIMIT 10
        """
    cur.execute(query, (session_id))
    result = cur.fetchall()
    data = []
    for row in result:
        data.append({
            "question": row[0],
            "id": row[1]
        })
    
    return data

def ask(question: str, session_id: str):
    # 1. Ambil pertanyaan sebelumnya
    get_history = find_question_only(session_id)
    if not get_history:
        return {"message": "Tidak ada pertanyaan dalam sesi ini."}

    # 2. Vektorkan setiap pertanyaan satu per satu dan simpan
    history_questions = []
    history_vectors = []
    for item in get_history:
        q = item["question"]
        v = model.encode(q)  # encode satu per satu
        history_questions.append(q)
        history_vectors.append(v)

    # 3. Vektorkan pertanyaan baru
    new_vector = model.encode(question)

    # 4. Hitung kemiripan satu per satu
    best_match = None
    best_score = -1
    for q, vec in zip(history_questions, history_vectors):
        score = cosine_similarity([new_vector], [vec])[0][0]
        if score > best_score:
            best_score = score
            best_match = q

    # 5. Return hasil terbaik
    return {
        "pertanyaan_baru": question,
        "pertanyaan_mirip": best_match,
        "skor_kemiripan": float(best_score)
    }
