import os
from dotenv import load_dotenv
from flask import jsonify
from connection.connection import get_connection
from datetime import datetime

from langchain.chat_models import init_chat_model
from langchain import hub
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

now = datetime.now()
current_month = now.strftime("%B") 
current_year = now.strftime("%Y") 
bulan_mapping = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember"
}

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = openai_api_key

# Melakukan konversi database
def convert(text):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return embeddings.embed_query(text)

# Melakukan macthing question di database
def match_question(question: str):
    q_vector = convert(question)
    if q_vector is None:
        return [{"article_content": "Tidak dapat melakukan konversi vektor"}]

    conn = get_connection()
    if not conn:
        return [{"article_content": "Tidak dapat melakukan koneksi ke database"}]

    try:
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
        cur.execute(query, (q_vector, q_vector))
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
                "article_content": f"""Mohon maaf pertanyaan anda mengenai {question} belum dapat saya jawab. Silakan hubungi helpdesk di 0812626260982 atau email nusa.net.id""",
                "similarity": "Tidak ada",
                "panjang": len(grouped)
            }]
        all_questions_list = [data["question"] for data in grouped.values()]
        combined_questions_newline = "\n".join(all_questions_list)
        for data in grouped.values():
            data["question"] = combined_questions_newline
        return list(grouped.values())

    except Exception as e:
        return [{"article_content": "Gagal query database: " + str(e)}]
    finally:
        cur.close()
        conn.close()

# Mencari session id user, untuk generate history pertanyaan
def find_session(session):
    if not session:
        return jsonify({"success": False, "message": "Parameter 'session' wajib diisi"}), 400

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            time,
            question,
            context,
            response,
            similar_question
        FROM
            log
        WHERE
            session_id = %s
    """

    cur.execute(query, (session,))
    result = cur.fetchall()

    data = []
    for row in result:
        data.append({
            "time": row[0],
            "question": row[1],
            "context": row[2],
            "response": row[3],
            "similar_question": row[4]
        })

    cur.close()
    conn.close()
    return data

# Melakukan penyimpanan pertanyaan user ke database yang memiliki  nilai konteks 
def save_log(data):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO log (
            session_id, time, question, similar_question, similarity,
            context, system_instruction, response
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """

    cur.execute(query, (
        data['session_id'],
        data['time'],
        data['question'],
        data['similar_question'], 
        data['similarity'],
        data['context'],
        data['system_instruction'],
        data['response']
    ))

    log_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return {"success": True, "log_id": log_id}

def join_question(history_list, question):
    return "".join(
        [f"{entry['similar_question']}".strip()
        for entry in history_list] + [question.strip()]
    )

def find_question_only(session_id):
    conn = get_connection()
    cur = conn.cursor()

    query= """
            SELECT 
                question,
                context
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
            "context": row[1]
        })
    
    return data

# Untuk melakukan pertanyaan 
def asktest(question: str, session_id:str):
    llm = ChatOpenAI(model="gpt-4o-mini")
    get_history = find_question_only(session_id)

    history_question = []
    history_vector = []
    for item in get_history:
        q = item["question"]
        v = convert(q)
        history_question.append(q)
        history_vector.append(v)
    

    new_q_vec = convert(question)
    best_match = None
    best_score = -1
    for q, vec in zip(history_question, history_vector):
        score = cosine_similarity([new_q_vec], [vec])[0][0]
        if score > best_score:
            best_score = score
            best_match = q

    # 5. Kembalikan hanya jika skor > 0.85
    if best_score >= 0.85:
        return {
            "pertanyaan_baru": question,
            "pertanyaan_mirip": best_match,
            "skor_kemiripan": float(best_score)
        }
    else:
        return {
            "pertanyaan_baru": question,
            "pertanyaan_mirip": None,
            "skor_kemiripan": float(best_score),
            "message": "Tidak ada pertanyaan yang cukup mirip (di atas 85%)"
        }



def ask(question: str, session_id:str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    # Cek session
    get_history = find_session(session_id)
    
    history = join_question(get_history, question)
    if history:
        # prompt sumarry
        prompt_summary = PromptTemplate.from_template("""  
                                Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant). Kamu akan membantu customer.
                                Tugas kamu disini adalah meringkas pertanyaan dari history percakapan sebelumnya. 
                                Dari history ini kamu akan meringkas pertanyaannya apa saja. Buatkan menjadi satu  buah pertanyaan yang merangkup seluruh pertanyaan-pertanyaan user sebelumnya.
                                Jawaban anda hanyalah pertanyaan, tidak perlu menambah penjelasan dan lainnya.
                                
                                Adapun history pertanyaan sebelumnya adalah:
                                {history}
                            """)
        reformat = prompt_summary.format(
            history = history
        )

        res_sum = llm.invoke(reformat)
    
        q_data = match_question(res_sum.content) # Ubah ke res.content
        #return history
        if not q_data or "articles" not in q_data[0]:
            prompt_notfound = PromptTemplate.from_template(
                                """
                                   Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant. Kamu adalah asisten cerdas yang akan membantu dalam meringkas history pertanyaan customer sebelumnya

                                   Saat ini artikel tidak ditemukan. Tugas kamu adalah memberikan informasi bahwa kamu belum bisa menjawab pertanyaan {question} yang diberikan dan arahkan untuk bertanya melalui kontak nusaneet yaitu nusa.net.id.
                                """
            )
       
            reformat = prompt_notfound.format(
                question = question
            )
            res = llm.invoke(reformat)


            data = {
                "session_id": session_id,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "question": res_sum.content,
                "similarity": "0",
                "similar_question": "",
                "context": "",
                "system_instruction": reformat,
                "response": res.content,
            }
            save_log(data)
            
            return res.content, "Not found article : Source ini berasal dari tidak ditemukan artikel part-1", res_sum.content
        
        #Gabungkan seluruh artikel
        join_article = set()
        part_context = []

        for entry in q_data:
            for article in entry["articles"]:
                if article["id"] not in join_article:
                    join_article.add(article["id"])
                    part_context.append(f"Judul: {article['title']}\n{article['content']}")

        context = "\n\n".join(part_context)

        prompt_answer = PromptTemplate.from_template(
            """
                Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant. Kamu adalah asisten cerdas yang akan membantu dalam meringkas history pertanyaan customer sebelumnya

                Aturan kamu sebagai asisten adalah:
                    1. Gunakan bahasa indonesia yang baik dan benar, serta profesional.
                    2. Selalu jawab pertanyaan sesuai dengan konteks, jangan menjelaskan apapun yang tidak sesuai
                    3. Informasi yang kamu berikan harus informatif dan jelas. Setiap ada kontak yang dapat dihubungi harus kamu sertakan.
                    4. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini {month} {year}
                    5. Jika ada informasi terkait di history harus kamu sertakan.
                                                     
                Berikut adalah history dari percakapan sebelumnya:
                {history}
                            
                Berikut adalah pertanyaan user:
                {question}

                Berikut adalah konteks terkait:
                {articles}
            """)
        
        reformat = prompt_answer.format(
            month = current_month,
            year = current_year,
            history = get_history,
            question = question,
            articles = context
        )

        res = llm.invoke(reformat)
        data = {
            "session_id": session_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "similarity": q_data[0]["similarity"],
            "similar_question": q_data[0]["question"],
            "context": context,
            "system_instruction": reformat,
            "response": res.content,
        }
        
        save_log(data)

        return res.content, q_data[0]["similarity"], "Ini berasal dari terdapat history dan question match"
    else:
        vec = convert (question)
        q_data = match_question(vec)
        if not q_data or "articles" not in q_data[0]:
            prompt_notfound = PromptTemplate.from_template(
                                """
                                   Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant. Kamu adalah asisten cerdas yang akan membantu dalam meringkas history pertanyaan customer sebelumnya

                                   Saat ini artikel tidak ditemukan. Tugas kamu adalah memberikan informasi bahwa kamu belum bisa menjawab pertanyaan {question} yang diberikan dan arahkan untuk bertanya melalui kontak nusaneet yaitu nusa.net.id.
                                """
            )
       
            reformat = prompt_notfound.format(
                question = question
            )
            res = llm.invoke(reformat)
            return res.content, "Not found article : Source ini berasal dari tidak ditemukan artikel part-2"
        
        #Gabungkan seluruh artikel
        join_article = set()
        part_context = []

        for entry in q_data:
            for article in entry["articles"]:
                if article["id"] not in join_article:
                    join_article.add(article["id"])
                    part_context.append(f"Judul: {article['title']}\n{article['content']}")

        context = "\n\n".join(part_context)

        prompt_answer = PromptTemplate.from_template(
            """
                Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant. Kamu adalah asisten cerdas yang akan membantu dalam meringkas history pertanyaan customer sebelumnya

                Aturan kamu sebagai asisten adalah:
                    1. Gunakan bahasa indonesia yang baik dan benar, serta profesional.
                    2. Selalu jawab pertanyaan sesuai dengan konteks, jangan menjelaskan apapun yang tidak sesuai
                    3. Informasi yang kamu berikan harus informatif dan jelas. Setiap ada kontak yang dapat dihubungi harus kamu sertakan.
                    4. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini {month} {year}
                    5. Jika ada informasi terkait di history harus kamu sertakan.
                                                     
                Berikut adalah history dari percakapan sebelumnya:
                {histor}
                            
                Berikut adalah pertanyaan user:
                {question}

                Berikut adalah konteks terkait:
                {articles}
            """)
        
        reformat = prompt_answer.format(
            month = current_month,
            year = current_year,
            history = history,
            question = question,
            article = context
        )

        res = llm.invoke(reformat)
    
        data = {
            "session_id": session_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "similarity": q_data[0]["similarity"],
            "similar_question": q_data[0]["question"],
            "context": context,
            "system_instruction": reformat,
            "response": res.content,
        }
        save_log(data)

        return res.content, q_data[0]["similarity"], "Ini berasal dari tidak terdapat history dan question match"

def asktest(question: str, session_id: str):
    

    current_month = bulan_mapping[now.strftime("%B")]


    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    history = find_session(session_id)
    # Jika history pertanyaan tidak ada:
    if not history:
        prompt_template = PromptTemplate.from_template(
            """
                Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant) asisten cerdas yang akan menjawab seluruh pertanyaan customer dengan baik berdasarkan informasi jawaban yang diberikan.

                Aturan kamu sebagai asisten:
                1. Jika konteks jawaban yang diberikan, tidak boleh kamu ringkas maupun kamu potong. Seluruh jawaban harus kamu berikan dengan baik.
                2. Jika ada informasi kontak baik itu Whatsapp, email, dan lainnya wajib kamu cantumkan.
                3. Jika ada pertanyaan yang tidak ada konteks jawaban, maka kamu jawab dengan baik dan meminta maaf.
                4. Selalu gunakan bahasa Indonesia yang baik dan benar.
                5. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini {month} {year}

                Berikut adalah konteks:
                {context}

                Pertanyaan: {question}

            
            """
        )

        # Ambil pertanyaan mirip
        q_data = match_question(question)

        if not q_data or "articles" not in q_data[0]:
            if history:
                prompt_temp = PromptTemplate.from_template(
                    """
                        Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant) asisten cerdas yang dapat membantu costumer dalam bergabagi masalahnya.
                        1. Selalu gunakan bahasa Indonesia yang baik dan benar.
                        2. Selalu kondisikan pertanyaan yang akan dikirimkan ke kamu, jika pertanyaanya punya informasi dari informasi history silahkan jawab, jika tidak ada informasi dari pertanyaan sialhakn menyuruh costumer untuk menghubungi nusa.net.id
                        3. Jika ada customer yang bertanya list pertanyaan yang telah diajukan, silahkan list pertanyaan yang ada pada story

                        Berikut adalah history data pertanyaan dan konteks jawaban percakapan :
                        {history}

                        dan berikut adalah pertanyaan costumer saat ini:
                        {question}
                    """
                )
                fallback_prompt = prompt_temp.format(
                    month=current_month,
                    year=current_year,
                    history = history,
                    question = question,
                )
                response = llm.invoke(fallback_prompt)
                return response.content, "Not found articles"
            else:
                fallback_prompt = prompt_template.format(
                    context="Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant). Maaf, saya tidak memiliki informasi yang relevan. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini"+current_month + current_year,
                    question=question
                )
                response = llm.invoke(fallback_prompt)
                return response.content, "tidak ada artikel"

        # Gabungkan semua artikel sebagai context
        seen_articles = set()
        context_parts = []

        for entry in q_data:
            for article in entry["articles"]:
                if article["id"] not in seen_articles:
                    seen_articles.add(article["id"])
                    context_parts.append(f"Judul: {article['title']}\n{article['content']}")

        context = "\n\n".join(context_parts)

        # Format prompt final
        final_prompt = prompt_template.format(
            month=current_month,
            year=current_year,
            context=context.strip(),
            question=question.strip(),
            
        )

        response = llm.invoke(final_prompt)

        data = {
            "session_id": session_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "similarity": q_data[0]["similarity"],
            "similar_question": q_data[0]["question"],
            "context": context,
            "system_instruction": final_prompt,
            "response": response.content,
        }
        save = save_log(data)
        return response.content, data["similarity"], context, save
    
    history_text = "\n\n".join(
            f"[{h['time']}]\nCustomer: {h['question']}\nBot: {h['response']}" for h in history
        )
    
    prompt_summary = PromptTemplate.from_template(
        """
            Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant) asisten cerdas yang akan meringkas seluruh informasi mengenai pertanyaan dan juga jawaban dari data percakapan histori.

            Aturan kamu sebagai assisten adalah:
            1. Selalu buat list pertannyaan dan jawaban yang sesuai dari data history yang diberikan.
            2. Jawaban harus informatif
            3. Gunakan bahasa indonesia yang baik dan benar.
            4. Jika selalu ada informasi mengenai kontak seperti no Whatsapp dan juga emali dan lainnya harus selalu kamu sertakan.
            5. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini {month} {year}

            Berikut adalah history dari pertanyaan dan jawaban:
            {history_text}
        """
    )
    formatted_prompt = prompt_summary.format(history_text=history_text, month=current_month, year=current_year)
    summary = llm.invoke(formatted_prompt)
    
    # Buat prompt template custom
    prompt_template = PromptTemplate.from_template(
        """
                Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant) asisten cerdas yang akan menjawab seluruh pertanyaan customer dengan baik berdasarkan informasi jawaban yang diberikan.

                Aturan kamu sebagai asisten:
                1. Jika konteks jawaban yang diberikan, tidak boleh kamu ringkas maupun kamu potong. Seluruh jawaban harus kamu berikan dengan baik.
                2. Jika ada informasi kontak baik itu Whatsapp, email, dan lainnya wajib kamu cantumkan.
                3. Jika ada pertanyaan yang tidak ada konteks jawaban, maka kamu jawab dengan baik dan meminta maaf.
                4. Selalu gunakan bahasa Indonesia yang baik dan benar.
                5. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikandan saat ini {month} {year}

                Berikut adalah informasi ringkasan pertanyaan dan jawaban sebelumnya
                {summary} // histroy, konteks, dan pertanyaan

                Berikut adalah history diskusi
                {context}

                Pertanyaan: {question}

            
        """
    )

    # Ambil pertanyaan mirip
    q_data = match_question(question)

    if not q_data or "articles" not in q_data[0]:
            # Jika ada history pertanyaan dan tidak ada jawaban pertanyaan di database
            if history:
                prompt_temp = PromptTemplate.from_template(
                    """
                        Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant) asisten cerdas yang dapat membantu costumer dalam bergabagi masalahnya.
                        1. Selalu gunakan bahasa Indonesia yang baik dan benar.
                        2.. Selalu kondisikan pertanyaan yang akan dikirimkan ke kamu, jika pertanyaanya punya informasi dari informasi history silahkan jawab, jika tidak ada informasi dari pertanyaan sialhakn menyuruh costumer untuk menghubungi nusa.net.id
                        3. Jika ada customer yang bertanya list pertanyaan yang telah diajukan, silahkan list pertanyaan yang ada pada story
                        4. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan dan saat ini {month} {year}

                        Berikut adalah history data pertanyaan dan konteks jawaban percakapan :
                        {history}

                        dan berikut adalah pertanyaan costumer saat ini:
                        {question}
                    """
                )
                fallback_prompt = prompt_temp.format(
                   month= current_month,
                    year = current_year,
                    history = history,
                    question = question,
                    
                )
                response = llm.invoke(fallback_prompt)
                return response.content, "Not found articles"
            else:
                fallback_prompt = prompt_template.format(
                    context="Kamu adalah Naila (Nusa Artificial Intelligance Liaison Assistant). Maaf, saya tidak memiliki informasi yang relevan. Kamu harus selalu ingat tanggal, bulan, dan tahun saat ini, sehingga jika ada pertanyaan terkait waktu, kamu harus bisa sesuaikan" + current_month+ current_year,
                    question=question
                )
                response = llm.invoke(fallback_prompt)
                return response.content, "tidak ada artikel"

        # Gabungkan semua artikel sebagai context
    seen_articles = set()
    context_parts = []

    for entry in q_data:
        for article in entry["articles"]:
            if article["id"] not in seen_articles:
                seen_articles.add(article["id"])
                context_parts.append(f"Judul: {article['title']}\n{article['content']}")

    context = "\n\n".join(context_parts)

        # Format prompt final
    final_prompt = prompt_template.format(
        month=current_month,
        year=current_year,
        summary=summary.content,
        context=context.strip(),
        question=question.strip(),
        
    )

    response = llm.invoke(final_prompt)

    data = {
            "session_id": session_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "similarity": q_data[0]["similarity"],
            "similar_question": q_data[0]["question"],
            "context": context,
            "system_instruction": final_prompt,
            "response": response.content,
    }
    save = save_log(data)
    return response.content, data["similarity"], context, save, summary.content
