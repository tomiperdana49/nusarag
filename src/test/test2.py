# test.py

import os
from dotenv import load_dotenv
import psycopg2
from langchain_openai import OpenAIEmbeddings

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def embed_question(question):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return embeddings.embed_query(question)

def run_similarity_search(question):
    vector = embed_question(question)
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT
            q.id AS question_id,
            q.question,
            (1 - (q.question_vector <=> %s::vector)) AS cosine_similarity,
            a.id AS article_id,
            a.title AS article_title,
            a.content AS article_content
        FROM
            questions q
        JOIN
            question_articles qa ON q.id = qa.question_id
        JOIN
            articles a ON qa.article_id = a.id
        WHERE
            (1 - (q.question_vector <=> %s::vector)) >= 0.7
        ORDER BY
            cosine_similarity DESC;
    """
    cur.execute(query, (vector,vector))
    results = cur.fetchall()

    if not results:
        print("Tidak ada hasil yang ditemukan.")
    else:
        for row in results:
            print("-" * 40)
            print(f"Question ID: {row[0]}")
            print(f"Pertanyaan: {row[1]}")
            print(f"Similarity: {row[2]:.4f}")
            print(f"Article ID: {row[3]}")
            print(f"Judul Artikel: {row[4]}")
            print(f"Isi Artikel: {row[5][:200]}...")  # batasi output isi

    cur.close()
    conn.close()

if __name__ == "__main__":
    pertanyaan = input("Masukkan pertanyaan: ")
    run_similarity_search(pertanyaan)
