import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_mail_issu(data):
    sender = "ragnusanet@gmail.com"
    sender_pass = "qziv vhjf ycft hhog"
    receiver_email = "josuapinem002@gmail.com"

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver_email
    msg['Subject'] = "User Question Issue - Otomatic Sender Mail"

    if not data["history"]:
        data["history"] = "Diskusi Pertama"

    body = f""" Halo, saya mendapatkan issu pada user dengan data sebagai berikut:
                \n\t Id         : {data["session_id"]}
                \n\t Organisasi : {data["organization_id"]}
                \n\t Pertanyaan : {data["question"]}
                \n\t History    : {data["history"]}
                
 
                \n\nHarap untuk tidak membalas pesan ini karena ini tidak menerima jawaban. Terima kasih.
            """
    msg.attach(MIMEText(body, 'plain'))
    # Kirim email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enkripsi TLS
        server.login(sender, sender_pass)
        server.sendmail(sender, receiver_email, msg.as_string())
        server.quit()
        return "Email berhasil dikirim!"
    except Exception as e:
        return f"Gagal mengirim email: {e}"
