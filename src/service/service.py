from connection.connection import get_connection
from model.model import convert, ask

class ArticleService:
    # Menginput artikel ke database
    def create_article(self, article):
        conn = get_connection()
        cur = conn.cursor()

        query = """
                    INSERT INTO articles (id, title, content, author, organization_id, status, created_by, updated_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        author = EXCLUDED.author,
                        organization_id = EXCLUDED.organization_id,
                        status = EXCLUDED.status,
                        created_by = EXCLUDED.created_by,
                        updated_by = EXCLUDED.updated_by
                    RETURNING *
                """


        values = [
            article.get("id"),
            article.get("title"),
            article.get("content"),
            article.get("author"),
            article.get("organization_id"),
            article.get("status", "draft"),
            article.get("created_by"),
            article.get("updated_by")
        ]

        cur.execute(query, values)
        result = cur.fetchone()
        column_names = [desc[0] for desc in cur.description]
        conn.commit()
        cur.close()
        conn.close()

        return dict(zip(column_names, result))
    
    def create_article_batch(self, pairs: list[dict]):
        conn = get_connection()
        cur = conn.cursor()
        try:
                for item in pairs:
                    article_id = item["id"]
                    title = item["title"]
                    content = item["content"]
                    author = item["author"]
                    organization_id = item["organization_id"]
                    status = item["status"]
                    created_by = item["created_by"]
                    updated_by = item["updated_by"]

                    cur.execute(
                        """
                        INSERT INTO articles (id, title, content, author, organization_id, status, created_by, updated_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id)
                                DO UPDATE SET
                                    title = EXCLUDED.title,
                                    content = EXCLUDED.content,
                                    author = EXCLUDED.author,
                                    organization_id = EXCLUDED.organization_id,
                                    status = EXCLUDED.status,
                                    created_by = EXCLUDED.created_by,
                                    updated_by = EXCLUDED.updated_by
                                RETURNING *
                        """,
                        (article_id, title, content, author, organization_id, status, created_by, updated_by)
                    )

                conn.commit()
                return {"success": True} 

        except Exception as e:
                conn.rollback()
                raise e

        finally:
                cur.close()
                conn.close()

    
    # Mengakses seluruh data artikel pada database
    def get_all_articles(self):
        conn = get_connection()
        cur = conn.cursor()

        query = """
                SELECT a.*, o.name AS organization_name
                FROM articles a
                LEFT JOIN organizations o ON a.organization_id = o.id
                ORDER BY a.created_at DESC
        """

        cur.execute(query)
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        return[dict(zip(column_names, row)) for row in rows]

    # Mengakses artikel berdasarkan id pada database
    def get_article_by_id(self, article_id):
        conn = get_connection()
        cur = conn.cursor()

        query = """
                SELECT a.*, o.name AS organization_name
                FROM articles a
                LEFT JOIN organizations o ON a.organization_id = o.id
                WHERE a.id = %s
        """

        cur.execute(query, (article_id))
        row = cur.fetchone()
        column_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        return dict(zip(column_names, row)) if row else None
    
    def getArticle_Id(self):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, title, content FROM articles ORDER BY ID ASC;")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        result = [dict(zip(columns, row)) for row in rows]
        return result

class QuestionService:
    def create_questions(self, questions):
        conn = get_connection()
        cur = conn.cursor()
        try:
            questions_vector = convert(questions.get("question"))
            if questions_vector is None:
                raise Exception("Gagal dalam mengkonversi vektor.")

            query = """
                INSERT INTO questions (
                    id, question, question_vector, organization_id, created_by, updated_by, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id)
                    DO UPDATE SET
                        question = EXCLUDED.question,
                        question_vector = EXCLUDED.question_vector,
                        organization_id = EXCLUDED.organization_id,
                        created_by = EXCLUDED.created_by,
                        updated_by = EXCLUDED.updated_by,
                        status = EXCLUDED.status
                RETURNING *;
            """

            updated_by = questions.get("updated_by") or questions.get("created_by")

            cur.execute(query, (
                questions.get("id"),
                questions.get("question"),
                questions_vector,
                questions.get("organization_id"),
                questions.get("created_by"),
                updated_by,
                questions.get("status"),
            ))

            question_id = cur.fetchone()[0]
            conn.commit()

            return {
                "id": question_id,
                "question": questions.get("question"),
                "organization_id": questions.get("organization_id")
            }

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            cur.close()
            conn.close()

    def create_question_batch(self, pairs: list[dict]):
        conn = get_connection()
        cur = conn.cursor()
        try:
                for item in pairs:
                    question_id = item["id"]
                    question = item["question"]
                    question_vector = convert(item["question"])
                    organization_id = item["organization_id"]
                    created_by = item["created_by"]
                    updated_by = item["updated_by"]
                    status = item["status"]

                    cur.execute(
                        """
                            INSERT INTO questions (
                                id, question, question_vector, organization_id, created_by, updated_by, status
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id)
                                DO UPDATE SET
                                    question = EXCLUDED.question,
                                    question_vector = EXCLUDED.question_vector,
                                    organization_id = EXCLUDED.organization_id,
                                    created_by = EXCLUDED.created_by,
                                    updated_by = EXCLUDED.updated_by,
                                    status = EXCLUDED.status
                            RETURNING *;
                        """,
                        (question_id, question, question_vector, organization_id, created_by, updated_by, status)
                    )

                conn.commit()
                return {"success": True} 

        except Exception as e:
                conn.rollback()
                raise e

        finally:
                cur.close()
                conn.close()



    def attach_articles_to_questions_batch(self, pairs: list[dict]):
        conn = get_connection()
        cur = conn.cursor()

        checkQ = list({q["question_id"] for q in pairs})
        checkA = list({a["article_id"] for a in pairs})

        cur.execute("SELECT id FROM questions WHERE id = ANY(%s)", (checkQ,))
        foundQ = {row[0] for row in cur.fetchall()}

        cur.execute("SELECT id FROM articles WHERE id = ANY(%s)", (checkA,))
        foundA = {row[0] for row in cur.fetchall()}

        missingQ = set(checkQ) - foundQ
        missingA = set(checkA) - foundA

        if missingQ or missingA:
            return {
                    "success": False,
                    "message": "ID tidak valid.",
                    "missing_questions": list(missingQ),
                    "missing_articles": list(missingA),
            }
            
        cur.execute("DELETE FROM question_articles;")
        conn.commit()
        try:
            for item in pairs:
                question_id = item["question_id"]
                article_id = item["article_id"]

                cur.execute(
                    """
                    INSERT INTO question_articles (question_id, article_id, created_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (question_id, article_id)
                    DO UPDATE SET
                        question_id = EXCLUDED.question_id,
                        article_id = EXCLUDED.article_id,
                        created_at = NOW()
                    RETURNING *;
                    """,
                    (question_id, article_id)
                )

            conn.commit()
            return {"success": True} 

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            cur.close()
            conn.close()

    def get_all_question(self):
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT 
                q.id AS question_id,
                q.question,
                q.status,
                q.created_by,
                q.updated_by,
                q.created_at,
                q.updated_at,
                q.organization_id,
                o.name AS organization_name,
                a.id AS article_id,
                a.title AS article_title,
                a.content AS article_content
            FROM questions q
            LEFT JOIN organizations o ON q.organization_id = o.id
            LEFT JOIN question_articles qa ON qa.question_id = q.id
            LEFT JOIN articles a ON a.id = qa.article_id
            ORDER BY q.id;
        """
        cur.execute(query)
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]

        result = {}
        for row in rows:
            row_dict = dict(zip(column_names, row))
            qid = row_dict["question_id"]
            if qid not in result:
                result[qid] = {
                    "id": qid,
                    "question": row_dict["question"],
                    "status": row_dict["status"],
                    "created_by": row_dict["created_by"],
                    "updated_by": row_dict["updated_by"],
                    "created_at": row_dict["created_at"],
                    "updated_at": row_dict["updated_at"],
                    "organization_id": row_dict["organization_id"],
                    "organization_name": row_dict["organization_name"],
                    "articles": []
                }
            if row_dict["article_id"]:
                result[qid]["articles"].append({
                    "article_id": row_dict["article_id"],
                    "title": row_dict["article_title"],
                    "content": row_dict["article_content"]
                })

        cur.close()
        conn.close()
        return list(result.values())

    def get_questions_by_id(self, questions_id):
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT 
                q.id AS question_id,
                q.question,
                q.status,
                q.created_by,
                q.updated_by,
                q.created_at,
                q.updated_at,
                q.organization_id,
                o.name AS organization_name,
                a.id AS article_id,
                a.title AS article_title,
                a.content AS article_content
            FROM questions q
            LEFT JOIN organizations o ON q.organization_id = o.id
            LEFT JOIN question_articles qa ON qa.question_id = q.id
            LEFT JOIN articles a ON a.id = qa.article_id
            WHERE q.id = %s;
        """
        cur.execute(query, (questions_id,))
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]

        if not rows:
            return None

        result = {
            "id": rows[0][0],
            "question": rows[0][1],
            "status": rows[0][2],
            "created_by": rows[0][3],
            "updated_by": rows[0][4],
            "created_at": rows[0][5],
            "updated_at": rows[0][6],
            "organization_id": rows[0][7],
            "organization_name": rows[0][8],
            "articles": []
        }

        for row in rows:
            if row[9]:
                result["articles"].append({
                    "article_id": row[9],
                    "title": row[10],
                    "content": row[11]
                })

        cur.close()
        conn.close()

        return result

class OrganizationService:
    def get_organizations(self):
        conn = get_connection()
        cur = conn.cursor()

        query= """
                SELECT id, name FROM organizations
            """
        
        cur.execute(query)
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        return[dict(zip(column_names, row)) for row in rows]
    
    def get_organizations_by_id(self, id):
        conn = get_connection()
        cur = conn.cursor()

        query = """
                    SELECT * FROM organizations
                    WHERE id=%s
                """
        
        cur.execute(query, (id))
        row = cur.fetchone()
        column_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        return dict(zip(column_names, row)) if row else None
    
    def create_organizations(self, organizations):
        conn = get_connection()
        cur = conn.cursor()
        query = """
            INSERT INTO organizations (name, created_at, updated_at)
            VALUES (%s, NOW(), NOW())
            RETURNING *
        """
        cur.execute(query, (organizations.get("name"),))  # <-- perbaikan di sini
        result = cur.fetchone()
        column_names = [desc[0] for desc in cur.description]
        conn.commit()
        cur.close()
        conn.close()

        return dict(zip(column_names, result))

    
class AskService:
    def asking(self, request_data: dict):
        question_text = request_data.get("question")
        user_id = request_data.get("session_id")
        organization_id = request_data.get("organization_id")
        if not question_text and user_id:
            raise ValueError("Kunci 'question' tidak ditemukan dalam body request JSON.")
        return ask(question_text, user_id, organization_id)

class LogService:
     def get_Log(self):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
                        SELECT
                            l.id,
                            l.session_id,
                            l.time,
                            o.name AS organization_id,
                            l.question,
                            l.similar_question,
                            l.similarity,
                            l.context,
                            l.system_instruction,
                            l.response,
                            l.summary,
                            l.sum_vector
                        FROM log l
                        LEFT JOIN organizations o
                            ON l.organization_id = o.id;
                    """)

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]  # Ambil nama kolom
        cur.close()
        conn.close()

        # Ubah setiap row menjadi dictionary
        result = [dict(zip(columns, row)) for row in rows]
        return result

class webHook:
    def setListenerHook(self, payload):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO hook_data (datas) VALUES (%s)", (payload,))
            conn.commit()
            print("✅ Payload berhasil disimpan")
        except Exception as e:
            print("❌ Error:", e)