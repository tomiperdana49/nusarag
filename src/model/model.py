import os

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
        return[{"article_content": "Tidak dapat melakukan konversi vektor"}]
    
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
                        (1 - (q.question_vector <=> %s::vector)) >= 0.7 AND q.organization_id = %s AND a.organization_id = %s
                    ORDER BY
                        cosine_similarity DESC;
                """
        cur.execute(query, (q_vector, q_vector, organization_id, organization_id))
        results = cur.fetchall()

        grouped = {}
        for row in results:
            qid = row[0]
            if qid not in grouped:
                grouped[qid] = {
                    "id_question": row[0],
                    "question": row[1],
                    "similarity": row[2],
                    "articles": []
                }
            
            grouped[qid]["articles"].append({
                "id": row[3],
                "title": row[4],
                "content": row[5]
            })
        
        if not grouped:
            return [{
                "question": question,
                "article_content": f"""Mohon maaf pertanyaan anda mengenai {question} belum dapat saya jawab. Silahkan hubungi nusa.net.id""",
                "similarity": "0",
            }]
        
        all_q_list = [data["question"] for data in grouped.values()]
        combined = "\n".join(all_q_list)
        for data in grouped.values():
            data["question"] = combined
        return list(grouped.values())
    
    except Exception as e:
        return [{"article_content": "Gagal query database: "+ str(e)}]
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
            sum_vector
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
            data['vector']
        ))

        log_id = cur.fetchone()[0]
        conn.commit()
        return {"success": True, "log_id": log_id}

    except Exception as e:
        conn.rollback()
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

        q_data = match_question(res_sum.content, organization_id)

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
                "vector": convert(res_sum.content)
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
                "similarity": "0",
                "context": context,
                "system_instruction": reformat_ans_h,
                "response": res_ans_h.content,
                "session_id": session_id,
                "summary": res_sum.content,
                "vector": convert(res_sum.content)
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
        q_data = match_question(question, organization_id)
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
                "vector": convert(question)
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
                "similarity": "0",
                "context": context,
                "system_instruction": reformat_ans,
                "response": res_ans.content,
                "session_id": session_id,
                "summary": "Percakapan awal",
                "vector": convert(question)
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




# Prompt template
prompt_sum = PromptTemplate.from_template(
    """
        Ringkaskan apa yang dimaksud penanya berikut ini dalam satu kalimat berdasarkan riwayat percakapan sebelumnya dan pertanyaan terakhir. Pastikan jawaban anda dalam bentuk pertanyaan bukan pernyataan.

        Riwayat percakapan sebelumnya:
        {history}

        Pertanyaan terakhir:
        {question}
    """
)

prompt_notfoundh = PromptTemplate.from_template(
    """
        Anda adalah asisten cerdas yang membantu Nusanet untuk menjawab pertanyaan yang tidak ada artikelnya.

        Aturan kamu dalam menjawab adalah:
        1. Gunakan bahasa indoensia yang baik dan benar serta sopan dan profesional. Dan buat responnya seperti meminta maaf juga.
        2. Karena artikel untuk menjawab pertanyaan tidak ada, silahkan menjawab untuk menghubungi nusa.net.id
        3. Tetapi jika ada informasi melalui history silahkan di jawab, namun harus sesuai konteks dari pertanyaan. Jika tidak ada konteks, jangan dijawab
        4. Ingat juga bahwa saat ini bulan {month} dan tahun {year}. Jika ada pertanyaan yang ada konteks waktu bulan dan tahun, sesuaikan dengan informasi bulan dan tahun saat ini. Jadi jangan memberikan inforami yang sudah berlalu jika ada konteks bulan dan tahunnya
        
        Adapun pertanyaan yang diajukan oleh user adalah
        {question}

        Adapun historynya adalah :
        {history}
    """
)

prompt_answrh = PromptTemplate.from_template(
    """
                Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant. Kamu adalah asisten cerdas yang akan membantu dalam meringkas history pertanyaan customer sebelumnya

                Aturan kamu sebagai asisten adalah:
                    1. Gunakan bahasa indonesia yang baik dan benar, serta profesional. Jangan pernah menyebutkan kata ringkasan.
                    2. Selalu jawab pertanyaan sesuai dengan konteks, jangan menjelaskan apapun yang tidak sesuai
                    3. Informasi yang kamu berikan harus informatif dan jelas. Setiap ada kontak yang dapat dihubungi harus kamu sertakan.
                    4. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini {month} {year}
                    5. Jika ada informasi terkait di history harus kamu sertakan.
                            
                Berikut adalah pertanyaan user:
                {question}

                Berikut adalah konteks terkait:
                {articles}

                Adapun history percakapan sebelumnya:
                {history}
    """)

prompt_notfound = PromptTemplate.from_template(
    """
        Anda adalah asisten cerdas yang membantu Nusanet untuk menjawab pertanyaan yang tidak ada artikelnya.

        Aturan kamu dalam menjawab adalah:
        1. Gunakan bahasa indoensia yang baik dan benar serta sopan dan profesional. Dan buat responnya seperti meminta maaf juga.
        2. Karena artikel untuk menjawab pertanyaan tidak ada, silahkan menjawab untuk menghubungi nusa.net.id
        3. Ingat juga bahwa saat ini bulan {month} dan tahun {year}. Jika ada pertanyaan yang ada konteks waktu bulan dan tahun, sesuaikan dengan informasi bulan dan tahun saat ini. Jadi jangan memberikan inforami yang sudah berlalu jika ada konteks bulan dan tahunnya
        
        Adapun pertanyaan yang diajukan oleh user adalah
        {question}
    """
)

prompt_answr = PromptTemplate.from_template(
    """
                Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant. Kamu adalah asisten cerdas yang akan membantu dalam meringkas history pertanyaan customer sebelumnya

                Aturan kamu sebagai asisten adalah:
                    1. Gunakan bahasa indonesia yang baik dan benar, serta profesional. Jangan pernah menyebutkan kata ringkasan                   2. Selalu jawab pertanyaan sesuai dengan konteks, jangan menjelaskan apapun yang tidak sesuai
                    3. Informasi yang kamu berikan harus informatif dan jelas. Setiap ada kontak yang dapat dihubungi harus kamu sertakan.
                    4. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini {month} {year}
                            
                Berikut adalah pertanyaan user:
                {question}

                Berikut adalah konteks terkait:
                {articles}

    """)


    