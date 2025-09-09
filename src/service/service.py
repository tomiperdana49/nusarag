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
        conn.commit()
        cur.close()
        conn.close()

        return result
    
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
        cur.close()
        conn.close()

        return rows

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
        cur.close()
        conn.close()

        return row if row else None
    
    def getArticle_Id(self):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, title, content FROM articles ORDER BY ID ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return rows

    def deleteArticle(self, articelId):
        conn = get_connection();
        cur = conn.cursor()

        cur.execute("DELETE FROM articles WHERE id = %s", (articelId.get("id"),))
        conn.commit()  # pastikan perubahan disimpan

        cur.close()
        conn.close()
        return "ok", 200

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
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()

        result = {}
        for row in rows:
            qid = row["question_id"]
            if qid not in result:
                result[qid] = {
                    "id": qid,
                    "question": row["question"],
                    "status": row["status"],
                    "created_by": row["created_by"],
                    "updated_by": row["updated_by"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "organization_id": row["organization_id"],
                    "organization_name": row["organization_name"],
                    "articles": []
                }
            if row["article_id"]:
                result[qid]["articles"].append({
                    "article_id": row["article_id"],
                    "title": row["article_title"],
                    "content": row["article_content"]
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
        cur = conn.cursor()
        cur.execute(query, (questions_id,))
        rows = cur.fetchall()

        if not rows:
            cur.close()
            conn.close()
            return None

        # karena rows sudah dict, bisa pakai key langsung
        result = {
            "id": rows[0]["question_id"],
            "question": rows[0]["question"],
            "status": rows[0]["status"],
            "created_by": rows[0]["created_by"],
            "updated_by": rows[0]["updated_by"],
            "created_at": rows[0]["created_at"],
            "updated_at": rows[0]["updated_at"],
            "organization_id": rows[0]["organization_id"],
            "organization_name": rows[0]["organization_name"],
            "articles": []
        }

        for row in rows:
            if row["article_id"]:
                result["articles"].append({
                    "article_id": row["article_id"],
                    "title": row["article_title"],
                    "content": row["article_content"]
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
        cur.close()
        conn.close()

        return rows
    
    def get_organizations_by_id(self, id):
        conn = get_connection()
        cur = conn.cursor()

        query = """
                    SELECT * FROM organizations
                    WHERE id=%s
                """
        
        cur.execute(query, (id))
        row = cur.fetchone()
        cur.close()
        conn.close()

        return row if row else None
    
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
        conn.commit()
        cur.close()
        conn.close()

        return result

    
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
                            l.ref
                        FROM log l
                        LEFT JOIN organizations o
                            ON l.organization_id = o.id;
                        ORDER BY l.time DESC
                    """)

        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

class webHook:
    def setListenerHook(self, payload):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO hook_data (datas) VALUES (%s)", (payload,))
            conn.commit()
            print("Payload berhasil disimpan")
        except Exception as e:
            print("Error:", e)