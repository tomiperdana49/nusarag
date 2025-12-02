import os, json

from dotenv import load_dotenv
from flask import jsonify
from datetime import datetime

# Import from file
from connection.connection import get_connection

# Import langchain
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate

from service.chat import notification

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
                        q.organization_id = %s
                    ORDER BY cosine_similarity DESC 
                    LIMIT 1;
                """
        cur.execute(query, (q_vector, organization_id,))
        results = cur.fetchall()

        grouped = {}
        for row in results:
            qid = row["question_id"]
            if qid not in grouped:
                grouped[qid] = {
                    "id_question": row["question_id"],
                    "question": row["question"],
                    "similarity": row["cosine_similarity"],  # angka asli dari query
                    "articles": []
                }

            grouped[qid]["articles"].append({
                "id": row["article_id"],
                "title": row["article_title"],
                "content": row["article_content"]
            })

        # karena LIMIT 1, pasti hanya ada 1 item
        if grouped:
            item = next(iter(grouped.values()))
            if item["similarity"] < 0.70:  # threshold 0.7 (karena hasil query range 0-1)
                return [{
                    "question": question,
                    "similar_question": item['question'],
                    "article_content": (
                        f"Mohon maaf pertanyaan anda mengenai {question} belum dapat saya jawab. "
                        f"Silahkan hubungi nusa.net.id. Gunakan Bahasa Indonesia atau Inggris sesuai dengan pertanyaan user {question}"
                    ),
                    "similarity": item["similarity"],  # tampilkan angka similarity asli
                }]
            return [item]

        # fallback kalau query tidak mengembalikan baris
        return [{
            "question": question,
            "article_content": (
                f"Mohon maaf pertanyaan anda mengenai {question} belum dapat saya jawab. "
                f"Silahkan hubungi nusa.net.id. Gunakan Bahasa Indonesia atau Inggris sesuai dengan pertanyaan user {question}"
            ),
            "similarity": 0,
        }]

    except Exception as e:
        return [{"article_content": "Gagal query database: " + str(e)}], []
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
            "question": row["question"],
            "response": row["response"]
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
        row = cur.fetchone()
        log_id = row["id"] if isinstance(row, tuple) else row["id"]
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
            time, session_id, organization_id, question, response, context
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        cur.execute(query, (
            data['time'],
            data['session_id'],
            data['organization_id'],
            data['question'],
            data['response'],
            data['context'],
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
    print("Hellow")

    history = find_history(session_id, organization_id)
    print(history)
    if history:
        try:
            reformat_sum = prompt_sum.format(
                history=history,
                question=question
            )
            res_sum = llm.invoke(reformat_sum)
            summary_text = getattr(res_sum, "content", "") or "Summary kosong"
            reformat_q = prompt_translate_h.format(
                history=summary_text
            )
            res_t = llm.invoke(reformat_q)
            translate_text = getattr(res_t, "content", "") or question

            q_data = match_question(translate_text, organization_id)
            if not q_data or not isinstance(q_data, list) or not q_data[0].get("articles"):
                reformat_notfoundh = prompt_notfoundh.format(
                    question=question,
                    history=history,
                    month=curr_month,
                    year=curr_year
                )
                res_nf = llm.invoke(reformat_notfoundh)
                response_text = getattr(res_nf, "content", "") or "Tidak ditemukan jawaban"

                save_log_dt = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "organization_id": organization_id,
                    "question": question,
                    "similar_question": q_data[0].get("similar_question"),
                    "similarity": q_data[0].get("similarity"),
                    "context": "Not Found",
                    "system_instruction": reformat_notfoundh,
                    "response": response_text,
                    "session_id": session_id,
                    "summary": summary_text,
                    "vector": convert(summary_text) if summary_text else None,
                }

                save_history_dt = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "session_id": session_id,
                    "organization_id": organization_id,
                    "question": question,
                    "response": response_text,
                    "context": "Not Found"
                }

                save_history(save_history_dt)
                save_log(save_log_dt)
                notification("Not Found", session_id, question)
                return response_text, summary_text, "Not found article", history, reformat_notfoundh

            join_article = set()
            part_context = []
            for entry in q_data:
                articles = entry.get("articles", [])
                if not isinstance(articles, list):
                    continue
                for article in articles:
                    if not article or "id" not in article:
                        continue
                    if article["id"] not in join_article:
                        join_article.add(article["id"])
                        part_context.append(
                            f"Judul: {article.get('title', 'Tanpa Judul')}\n{article.get('content', '')}"
                        )

            context = "\n".join(part_context) if part_context else "Tidak ada artikel valid"

            reformat_ans_h = prompt_answrh.format(
                question=question,
                articles=context,
                month=curr_month,
                year=curr_year,
                history=history
            )
            res_ans_h = llm.invoke(reformat_ans_h)
            response_text = getattr(res_ans_h, "content", "") or "Jawaban kosong"

            save_log_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "organization_id": organization_id,
                "question": question,
                "similar_question": q_data[0].get("question", "Unknown"),
                "similarity": q_data[0].get("similarity", "0"),
                "context": context,
                "system_instruction": reformat_ans_h,
                "response": response_text,
                "session_id": session_id,
                "summary": summary_text,
                "vector": convert(summary_text) if summary_text else None,
            }

            save_history_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "organization_id": organization_id,
                "question": question,
                "response": response_text,
                "context": context,
            }
            save_history(save_history_dt)
            save_log(save_log_dt)
            notification("Article Found", session_id, question)
            return response_text, summary_text, "Article Found"
        except Exception as e:
            import traceback
            err_msg = f"Internal error: {e}"
            print(err_msg)
            print(traceback.format_exc())
            return {
                "error": "1",
                "message": err_msg,
                "success": False}
    else:
        reformat_q = prompt_translate.format(
            question = question
        )
        res_tranlate = llm.invoke(reformat_q)
        q_data= match_question(res_tranlate.content, organization_id)
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
                "similar_question": q_data[0].get("similar_question"),
                "similarity": q_data[0].get("similarity"),
                "context": "Not Found",
                "system_instruction": reformat_notfound,
                "response": res_nf.content,
                "session_id": session_id,
                "summary": "Not Have Summary",
                "vector": convert(question),
            }

            save_history_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "organization_id": organization_id,
                "question": question,
                "response": res_nf.content,
                "context": "Not Found"
            }

            save_history(save_history_dt)
            save_log(save_log_dt)
            notification("Not Found", session_id, question)
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
            }

        save_history_dt = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "organization_id": organization_id,
                "question": question,
                "response": res_ans.content,
                "context": context
            }

        save_history(save_history_dt)
        save_log(save_log_dt)
        notification("Article Found", session_id, question)

        return res_ans.content, "Article Found"

# def check_question(question: str):
#     llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
#     reformat = prompt_check.format(
#         question=question
#     )
#     res_ans = llm.invoke(reformat)
#     print(res_ans.content)
#     return res_ans.content


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
        - Ingat yang kamu ringkas hanya pertanyaan (question) tidak ikut context nya!

        Riwayat percakapan sebelumnya:
        {history}
        Pertanyaan terakhir:
        {question}
        Hasil (1 pertanyaan tunggal) dalam bahasa yang sesuai dengan pertanyaan terakhir tanpa ikut meringkas context pada Riwayat:
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
        5. Pastikan format jawaban yang kamu berikan bagus untuk tampilan chat di Whatsapp

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
        6. Pastikan format jawaban yang kamu berikan bagus untuk tampilan chat di Whatsapp

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
        4. Pastikan format jawaban yang kamu berikan bagus untuk tampilan chat di Whatsapp

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
        6. Pastikan format jawaban yang kamu berikan bagus untuk tampilan chat di Whatsapp

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

prompt_check = PromptTemplate.from_template(
    """
    Kamu adalah asisten cerdas resmi dari PT. Media Antar Nusa (Nusanet),
    perusahaan teknologi penyedia layanan internet, cloud, dan aplikasi HRIS bernama Nusawork.

    === TUJUAN TUGAS ===
    Kamu akan mengevaluasi inputan user berikut:
    "{question}"

    === LANGKAH PENILAIAN ===
    1. **Apakah inputan merupakan pertanyaan?**
       - Analisa terlebih dahulu, jika memang bukan pertanyaan namun masih mengarah ke pembahasan Nusanet atau Nusawork (HRIS milik Nusanet). Silahkan dilanjutkan.
       - Jika bukan pertanyaan (hanya sapaan, kata pendek, atau teks umum) → langsung buat respon ramah & natural (lihat aturan di bawah).
       - Jika pertanyaan → lanjut ke langkah 2.

    2. **Jika pertanyaan, tentukan apakah BERKAITAN DENGAN NUSANET ataupun LAYANAN INTERNET, KELUHAN CUSTOMER, DAN LAINNYA YANG BERKAITAN MENGENAI CUSTOMER, INTERNET, DAN KARYAWAN.**
       Pertanyaan dianggap berkaitan dengan Nusanet jika termasuk dalam kategori berikut:
       - Tentang layanan internet, gangguan koneksi, modem, tagihan, atau CS.
       - Tentang produk atau merek internal seperti: **Nusafiber, Nusawork, Gamas, NusaContact, Wardix, Nusanet Cloud**, dll.
       - Tentang promo, harga, paket, pendaftaran, rekrutmen, atau lowongan kerja.
       - Tentang sistem, aplikasi, atau produk buatan Nusanet.
       - Tentang **identitas kamu sendiri** (misalnya: “kamu siapa?”, “apakah kamu dari Nusanet?”, “kamu AI apa?”, “siapa yang bikin kamu?”)
         → Ini **tetap dianggap relevan**, karena kamu adalah bagian dari Nusanet.
       - Tentang seputar karyawan, pelayanan nusanet terhadap karyawan, pengembangan karir dan lainnya yang berkaitan karyawan dan lowongan kerja ataupun yang berkaitan dengan HRD di Nusanet
         → Apakah di perusahaan ini adal lowongan kerja?, Apakah Nusanet ada training?, Tes seleksinya? dan lainnya.
       - Tentang seputar daerah
         → misalnya: medan, bali, binjai. keluarkan hanya `True` (tanpa tanda kutip, tanpa tambahan lain).

       Jika pertanyaan termasuk salah satu dari hal di atas → keluarkan **hanya teks berikut (tanpa tambahan apapun): True

       Jika pertanyaan tidak ada kaitannya dengan Nusanet (contoh: cuaca, politik, makanan, hobi, gosip, dll) → berikan jawaban sopan dan informatif:
       - Jelaskan bahwa kamu hanya membantu urusan terkait layanan, produk, dan informasi dari PT. Media Antar Nusa (Nusanet).
       - Berikan sedikit informasi positif tentang Nusanet agar user tertarik.
       - Akhiri dengan ajakan seperti “Ada hal seputar Nusanet yang ingin kamu tanyakan?”

    3. **Jika bukan pertanyaan (sapaan, salam, atau teks singkat):**
        - Jawab secara ramah dan alami, seolah kamu asisten manusia dari Nusanet yang antusias dan tulus.
        - Hindari kalimat template. Variasikan gaya bicaramu (kadang formal, kadang santai, tapi selalu sopan).
        - Pastikan respon kamu terasa manusiawi, bukan hasil salinan pola sebelumnya.
        - Gunakan variasi kecil seperti menyebut nama perusahaan (“tim Nusanet”), atau menambahkan sentuhan empati ringan.

        Contoh pola yang bisa kamu tiru (boleh dikombinasikan secara bebas):
        - User: “Hai” → Kamu:
            - “Hai juga! Senang banget bisa nyapa kamu. Ada yang bisa dibantu hari ini?”
            - “Halo! Terima kasih udah mampir, mau tanya soal layanan Nusanet?”
        - User: “Halo” → Kamu:
            - “Halo juga! Gimana kabarnya hari ini? Ada yang mau kamu cek di layanan Nusanet?”
            - “Halo! Saya siap bantu apa pun soal internet atau aplikasi HRIS dari Nusanet.”
        - User: “Pagi” → Kamu:
            - “Selamat pagi! Semoga hari kamu lancar dan menyenangkan. Mau tahu info promo Nusanet?”
            - “Pagi juga! Saya di sini siap bantu kamu soal layanan Nusanet.”
        - User: “Terima kasih” → Kamu:
            - “Sama-sama! Senang bisa bantu kamu. Kalau nanti ada yang mau ditanya, tinggal sapa aja ya 😊”
            - “Dengan senang hati! Pelayanan pelanggan adalah prioritas kami di Nusanet. Semoga harimu menyenangkan.”
            - “Wah, terima kasih kembali! Saya senang bisa bantu. Jangan sungkan kalau mau nanya apa pun seputar Nusanet.”
            - “Sama-sama! Senang rasanya bisa bantu kamu. Kalau ada kendala lain, tinggal kabari aja ya.”
            - “Terima kasih juga! Kami di Nusanet senang bisa melayani kamu. Semoga koneksi dan harimu lancar!”

        - Hindari pengulangan struktur kalimat yang sama.
        - Gunakan nada positif, hangat, dan empatik — tidak kaku seperti bot.


    === CONTOH OUTPUT ===
    - Input: “Internet saya mati, kenapa ya?” → Output: `True`
    - Input: “Ada promo paket internet gak?” → Output: `True`
    - Input: “Kamu siapa?” → Output: `True`
    - Input: “Ada gamas?” → Output: `True`
    - Input: “Hai” → Output: “Hai juga! Senang bisa terhubung. Ada yang bisa saya bantu hari ini?”
    - Input: “Cuaca di Bandung gimana?” → Output: “Hmm, untuk urusan cuaca saya kurang tahu, tapi saya bisa bantu seputar layanan internet dan HRIS dari Nusanet. Ada yang ingin kamu tanyakan soal itu?”

    === CATATAN TEKNIS ===
    Output kamu akan diproses oleh sistem Python.
    - Jika pertanyaan relevan dengan Nusanet → keluarkan hanya `True` (tanpa tanda kutip, tanpa tambahan lain).
    - Jika pertanyaan tidak relevan → jawab sopan dan singkat.
    - Jika bukan pertanyaan → berikan sapaan ramah yang variatif dan natural.
    - Jika user menyebutkan nama lokasi → keluarkan hanya `True` (tanpa tanda kutip, tanpa tambahan lain).
    """
)

