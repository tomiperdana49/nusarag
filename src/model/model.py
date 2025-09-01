import os, json

from dotenv import load_dotenv
from flask import jsonify
from datetime import datetime

# Import from file
from connection.connection import get_connection
from service.email_sender import send_mail_issu

# Import langchain
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate

# Creating datetime
now = datetime.now()
curr_month = now.strftime("%B")
curr_year = now.strftime("%Y")


# Akses File Env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = openai_api_key

# Melakukan konversi teks ke vektor
def convert(question: str):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return embeddings.embed_query(question)

# Melakukan match question ke database
def match_question(question:str, organization_id: int):
    conn = get_connection()
    cur = conn.cursor()
    # Konversi question ke vektor
    q_vector = convert(question)

    if q_vector is None:
        return[{"article_content": "Tidak dapat melakukan konversi vektor"}],[]
    try:
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
                        q.organization_id = %s
                """
        cur.execute(query, (q_vector, organization_id,))
        getData = cur.fetchall()
        results = []
        filltered = []

        for row in getData:
            sim = row["cosine_similarity"]
            if sim >= 0.7:
                results.append(row)
            else:
                filltered.append({
                    "question": row["question"],        # bukan row[1]
                    "article_title": row["article_title"],  # bukan row[3]
                    "cosine_similarity": sim
                })

        filltered_str = "\n\n".join(
            f"{item['question']}\n{item['article_title']}\n{item['cosine_similarity']:.2f}"
            for item in filltered
        )

        grouped = {}
        for row in results:
            qid = row["question_id"]  # pastikan nama kolom sesuai query SELECT
            if qid not in grouped:
                grouped[qid] = {
                    "id_question": row["question_id"],
                    "question": row["question"],
                    "similarity": row["cosine_similarity"],
                    "articles": []
                }
            
            grouped[qid]["articles"].append({
                "id": row["article_id"],
                "title": row["article_title"],
                "content": row["article_content"]
            })

        
        if not grouped:
            return [{
                "question": question,
                "article_content": f"""Mohon maaf pertanyaan anda mengenai {question} belum dapat saya jawab. Silahkan hubungi nusa.net.id. Gunakan Bahasa Indonesia atau Inggris sesuai dengan pertanyaan user {question}""",
                "similarity": "0",
            }], filltered_str
        
        all_q_list = [data["question"] for data in grouped.values()]
        combined = "\n".join(all_q_list)
        for data in grouped.values():
            data["question"] = combined
        return list(grouped.values()), filltered_str
    
    except Exception as e:
        return [{"article_content": "Gagal query database: "+ str(e)}], []
    finally:
        cur.close()
        conn.close()

# Melakukan pencarian history
def find_history(session_id, organization_id):
    if not session_id or not organization_id:
        return jsonify({"success": False, "message": "Session dan Organization wajib diisi"}), 400

    conn = get_connection()
    cur = conn.cursor()

    query = """
                SELECT
                    question,
                    response
                FROM
                    history
                WHERE
                    session_id = %s
                    AND organization_id = %s
                    AND time >= NOW() - INTERVAL '24 HOURS'
                ORDER BY
                    time DESC
                LIMIT 10;
            """
    
    cur.execute(query, (session_id, organization_id))
    result = cur.fetchall()
    
    data = []
    for row in result:
        data.append({
            "question": row[0],
            "response": row[1]
        })

    cur.close()
    conn.close()

    return data 

# Menyimpan seluruh informasi percakapan
import traceback

def save_log(data):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO log (
            time,
            organization_id,
            question,
            similar_question,
            similarity,
            context,
            system_instruction,
            response,
            session_id,
            summary,
            sum_vector,
            ref
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
    """

    try:
        cur.execute(query, (
            data['time'],
            data['organization_id'],
            data['question'],
            data['similar_question'],
            data['similarity'],
            data['context'],
            data['system_instruction'],
            data['response'],
            data['session_id'],
            data['summary'],
            data['vector'],
            data['ref']
        ))
        row = cur.fetchone()
        log_id = row[0] if isinstance(row, tuple) else row["id"]
        conn.commit()
        return {"success": True, "log_id": log_id}

    except Exception as e:
        conn.rollback()
        print("❌ Error saat insert log:")
        traceback.print_exc()  # <<=== ini akan tampilkan error lengkap
        return {"success": False, "error": str(e)}

    finally:
        cur.close()
        conn.close()



# Menyimpan history
def save_history(data):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO history (
            time, session_id, organization_id, question, response
        )
        VALUES (%s, %s, %s, %s, %s)
    """

    try:
        cur.execute(query, (
            data['time'],
            data['session_id'],
            data['organization_id'],
            data['question'],
            data['response']
        ))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


# Mengajukan pertanyaan
def ask(question: str, session_id: str, organization_id: int):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    history = find_history(session_id, organization_id)

    if history:
        reformat_sum = prompt_sum.format(
            history = history,
            question = question
        )

        res_sum = llm.invoke(reformat_sum)

        reformat_q = prompt_translate_h.format(
            history = res_sum.content
        )
        res_t = llm.invoke(reformat_q)

        q_data, refrece = match_question(res_t.content, organization_id)

        if not q_data or "articles" not in q_data[0]:
            reformat_notfoundh = prompt_notfoundh.format(
                question = question,
                history = history,
                month = curr_month,
                year = curr_year
            )

            res_nf = llm.invoke(reformat_notfoundh)

            save_log_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "organization_id": organization_id,
                "question": question,
                "similar_question": "Not Found",
                "similarity": "0",
                "context": "Not Found",
                "system_instruction": reformat_notfoundh,
                "response": res_nf.content,
                "session_id": session_id,
                "summary": res_sum.content,
                "vector": convert(res_sum.content),
                "ref": refrece
            }

            save_history_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "organization_id": organization_id,
                "question": question,
                "response": res_nf.content
            }

            save_history(save_history_dt)
            save_log(save_log_dt)

            data = {
                "session_id": session_id,
                "organization_id": organization_id,
                "question" : question,
                "history"   : res_sum.content
            }

            #send_mail_issu(data)

            return res_nf.content, res_sum.content, "Not found article", history, reformat_notfoundh

        join_article = set()
        part_context = []

        for entry in q_data:
            for article in entry["articles"]:
                if article["id"] not in join_article:
                    join_article.add(article["id"])
                    part_context.append(f"Judul: {article['title']}\n{article['content']}")

        context = "\n".join(part_context)

        reformat_ans_h = prompt_answrh.format(
            question = question,
            articles = context,
            month = curr_month,
            year = curr_year,
            history = history
        )

        res_ans_h = llm.invoke(reformat_ans_h)
        save_log_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "organization_id": organization_id,
                "question": question,
                "similar_question": q_data[0]["question"],
                "similarity": q_data[0]["similarity"],
                "context": context,
                "system_instruction": reformat_ans_h,
                "response": res_ans_h.content,
                "session_id": session_id,
                "summary": res_sum.content,
                "vector": convert(res_sum.content),
                "ref": refrece
            }

        save_history_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "organization_id": organization_id,
                "question": question,
                "response": res_ans_h.content
            }

        save_history(save_history_dt)
        save_log(save_log_dt)

        return res_ans_h.content, res_sum.content, "Article Found"
    else:
        reformat_q = prompt_translate.format(
            question = question
        )
        res_tranlate = llm.invoke(reformat_q)
        q_data, refrece = match_question(res_tranlate.content, organization_id)
        if not q_data or "articles" not in q_data[0]:
            
            reformat_notfound = prompt_notfound.format(
                question = question,
                month = curr_month,
                year = curr_year
            )

            res_nf = llm.invoke(reformat_notfound)

            save_log_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "organization_id": organization_id,
                "question": question,
                "similar_question": "Not Found",
                "similarity": "0",
                "context": "Not Found",
                "system_instruction": reformat_notfound,
                "response": res_nf.content,
                "session_id": session_id,
                "summary": "Not Have Summary",
                "vector": convert(question),
                "ref": refrece
            }

            save_history_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "organization_id": organization_id,
                "question": question,
                "response": res_nf.content
            }

            save_history(save_history_dt)
            save_log(save_log_dt)
            data = {
                "session_id": session_id,
                "organization_id": organization_id,
                "question" : question,
                "history" : "Tidak ada history"
            }

            #send_mail_issu(data)
            return res_nf.content, "Article Not Found"
     
        join_article = set()
        part_context = []
        for entry in q_data:
            for article in entry["articles"]:
                if article["id"] not in join_article:
                    join_article.add(article["id"])
                    part_context.append(f"Judul: {article['title']}\n{article['content']}")

        context = "\n".join(part_context)

        reformat_ans = prompt_answr.format(
            question = question,
            articles = context,
            month = curr_month,
            year = curr_year,
        )

        res_ans = llm.invoke(reformat_ans)
        save_log_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "organization_id": organization_id,
                "question": question,
                "similar_question": q_data[0]["question"],
                "similarity": q_data[0]["similarity"],
                "context": context,
                "system_instruction": reformat_ans,
                "response": res_ans.content,
                "session_id": session_id,
                "summary": "Percakapan awal",
                "vector": convert(question),
                "ref": refrece
            }

        save_history_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "organization_id": organization_id,
                "question": question,
                "response": res_ans.content
            }

        save_history(save_history_dt)
        save_log(save_log_dt)

        return res_ans.content, "Article Found"




prompt_sum = PromptTemplate.from_template(
    """
        ⚠️ RULE PENTING:
        Selalu deteksi bahasa dari {question} dan JAWAB dengan bahasa YANG SAMA.
        Jika user pakai bahasa Inggris → jawab dalam bahasa Inggris.
        Jika user pakai bahasa Indonesia → jawab dalam bahasa Indonesia.
        Jika campuran, pilih bahasa yang paling dominan.

        Tugas pertama kamu adalah mendeteksi bahasa yang digunakan oleh user melalui {question}. 
        Gunakan bahasa serupa dalam menjawab.
        Gabungkan informasi dari riwayat pertanyaan sebelumnya dengan pertanyaan terakhir
        untuk membentuk satu pertanyaan tunggal yang jelas, ringkas, dan lengkap.

        - Pastikan semua konteks penting dari riwayat pertanyaan tetap ada.
        - Hindari menyalin mentah pertanyaan terakhir, tapi perjelas maksudnya tanpa mengubah makna.
        - Gunakan bahasa Indonesia atau Inggris (sesuai dengan bahasa pertanyaan terakhir user).
        - Jika ada pertanyaan campuran, gunakan bahasa yang paling dominan.

        Riwayat percakapan sebelumnya:
        {history}
        Pertanyaan terakhir:
        {question}
        Hasil (1 pertanyaan tunggal) dalam bahasa yang sesuai dengan pertanyaan terakhir:
    """
)

prompt_notfoundh = PromptTemplate.from_template(
    """
        ⚠️ RULE PENTING:
        Selalu deteksi bahasa dari {question} dan JAWAB dengan bahasa YANG SAMA.
        Jika user pakai bahasa Inggris → jawab dalam bahasa Inggris.
        Jika user pakai bahasa Indonesia → jawab dalam bahasa Indonesia.
        Ingat apapun yang terjadi gunakan bahasa yang sesuai dengan bahasa pertanyaan.

        Anda adalah asisten cerdas yang membantu Nusanet untuk menjawab pertanyaan yang tidak ada artikelnya.

        Aturan kamu dalam menjawab adalah:
        1. Gunakan bahasa Indonesia atau Inggris (sesuai bahasa user) yang baik, benar, sopan, dan profesional. 
           Buat responnya seperti meminta maaf juga. 
        2. Karena artikel tidak ada, arahkan user untuk menghubungi nusa.net.id.
        3. Jika ada informasi melalui history, silakan jawab sesuai konteks. Jika tidak ada konteks, jangan dijawab.
        4. Ingat juga saat ini bulan {month} dan tahun {year}. Jika ada pertanyaan terkait waktu, sesuaikan dengan bulan & tahun saat ini. 
           Jangan memberi informasi yang sudah berlalu.

        Adapun pertanyaan yang diajukan oleh user adalah:
        {question}

        Adapun historynya adalah:
        {history}
    """
)

prompt_answrh = PromptTemplate.from_template(
    """
        ⚠️ RULE PENTING:
        Selalu deteksi bahasa dari {question} dan JAWAB dengan bahasa YANG SAMA.
        Jika user pakai bahasa Inggris → jawab dalam bahasa Inggris.
        Jika user pakai bahasa Indonesia → jawab dalam bahasa Indonesia.
        Ingat jika konteks terkait ataupun history menggunakan bahasa indonesia tapi pertanyaan menggunakan bahasa inggris translate semuanya sehingga anda tetap menjawab kedalam bahasa inggris

        Kamu adalah Naila (Nusa Artificial Intelligence Liaison Assistant). 
        Kamu adalah asisten cerdas yang membantu meringkas history pertanyaan customer sebelumnya.

        Aturan kamu sebagai asisten adalah:
        1. Gunakan bahasa Indonesia atau Inggris (sesuai bahasa user) yang baik dan profesional. 
           Jangan pernah menyebutkan kata ringkasan.
        2. Jawab pertanyaan sesuai konteks, jangan menjelaskan yang tidak relevan.
        3. Informasi harus jelas dan informatif. Jika ada kontak yang bisa dihubungi, sertakan.
        4. Ingat tanggal, bulan, dan tahun saat ini: {month} {year}.
        5. Jika ada informasi terkait di history, sertakan.

        Berikut adalah pertanyaan user:
        {question}

        Berikut adalah konteks terkait:
        {articles}

        Adapun history percakapan sebelumnya:
        {history}
    """
)

prompt_notfound = PromptTemplate.from_template(
    """
        ⚠️ RULE PENTING:
        Selalu deteksi bahasa dari {question} dan JAWAB dengan bahasa YANG SAMA.
        Jika user pakai bahasa Inggris → jawab dalam bahasa Inggris.
        Jika user pakai bahasa Indonesia → jawab dalam bahasa Indonesia.

        Anda adalah asisten cerdas yang membantu Nusanet untuk menjawab pertanyaan yang tidak ada artikelnya.

        Aturan kamu dalam menjawab adalah:
        1. Gunakan bahasa Indonesia atau Inggris (sesuai bahasa user) yang baik, benar, sopan, dan profesional. 
           Buat responnya seperti meminta maaf juga.
        2. Karena artikel tidak ada, arahkan user untuk menghubungi nusa.net.id.
        3. Ingat juga saat ini bulan {month} dan tahun {year}. Jika ada pertanyaan terkait waktu, sesuaikan dengan bulan & tahun saat ini. 
           Jangan memberi informasi yang sudah berlalu.

        Adapun pertanyaan yang diajukan oleh user adalah:
        {question}
    """
)

prompt_answr = PromptTemplate.from_template(
    """
        ⚠️ RULE SUPER PENTING:
        Jawablah SELALU dengan bahasa yang sama seperti pertanyaan user ({question}).
        - Jika user pakai bahasa Inggris → terjemahkan semua artikel {articles} ke bahasa Inggris sebelum menjawab.
        - Jika user pakai bahasa Indonesia → jawab dengan bahasa Indonesia.
        - Jika campuran, gunakan bahasa dominan user.

        Kamu adalah Naila (Nusa Artificial Intelligence Liaison Assistant).
        Kamu asisten cerdas yang membantu meringkas informasi untuk user.

        Aturan menjawab:
        1. Gunakan bahasa {question} sebagai patokan.
        2. Jangan pernah menjawab dengan bahasa lain meskipun artikel {articles} berbeda bahasa.
        3. Jawab profesional, jelas, informatif. Sertakan kontak jika relevan.
        4. Ingat sekarang bulan {month} {year}.
        5. Jika ada history, gunakan sesuai konteks.

        Pertanyaan user:
        {question}

        Artikel terkait (bisa berbeda bahasa, translate dulu ke bahasa user!):
        {articles}
    """
)


prompt_translate = PromptTemplate.from_template(
    """
        Tugas kamu adalah menerjemahkan pertanyaan berikut ke dalam bahasa Indonesia, 
        khusus untuk kebutuhan pencarian artikel di knowledge base.

        Aturan:
        1. Jika pertanyaan sudah menggunakan bahasa Indonesia → jangan diterjemahkan, kembalikan persis sama tanpa perubahan.
        2. Jika pertanyaan menggunakan bahasa Inggris → terjemahkan ke bahasa Indonesia.
        3. Jika pertanyaan campuran (Indonesia + Inggris) → terjemahkan semua ke bahasa Indonesia.
        4. Jangan menambah atau mengurangi kata. Pertahankan tanda baca, simbol tanya (?), dan format aslinya.

        Pertanyaan user: {question}

        Hasil (pertanyaan dalam bahasa Indonesia):
    """
)

prompt_translate_h = PromptTemplate.from_template(
    """
        Tugas kamu adalah menerjemahkan gabungan riwayat pertanyaan berikut ke dalam bahasa Indonesia,
        khusus untuk kebutuhan pencarian artikel di knowledge base.

        Aturan:
        1. Jika teks sudah menggunakan bahasa Indonesia → jangan diterjemahkan, kembalikan persis sama tanpa perubahan.
        2. Jika teks menggunakan bahasa Inggris → terjemahkan ke bahasa Indonesia.
        3. Jika teks campuran (Indonesia + Inggris) → terjemahkan semua ke bahasa Indonesia.
        4. Jangan menambah atau mengurangi kata. Pertahankan tanda baca, simbol tanya (?), dan format aslinya.

        Riwayat pertanyaan user: {history}

        Hasil (dalam bahasa Indonesia):
    """
)
