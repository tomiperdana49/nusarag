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

    body = f"""
                Halo, saya mendapatkan issu pada user dengan data sebagai berikut:
                \n\t Id         : {data["session_id"]}
                \n\t Organisasi : {data["organization_id"]}
                \n\t Pertanyaan : {data["question"]}
                
 
                \n\nHarap untuk tidak membalas pesan ini karena ini tidak menerima jawaban. Terima kasih.
            """
    msg.attach(MIMEText(body, 'plain'))
    # Kirim email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enkripsi TLS
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        return "Email berhasil dikirim!"
        server.quit()
    except Exception as e:
        return f"Gagal mengirim email: {e}"




# Informasi akun pengirim
sender_email = "ragnusanet@gmail.com"
sender_password = "qziv vhjf ycft hhog"  # atau App Password jika pakai Gmail 2FA
receiver_email = "josuapinem002@gmail.com"

# Buat pesan email
msg = MIMEMultipart()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = "Contoh Email dari Python"

body = "Halo, ini adalah email yang dikirim dari script Python."
msg.attach(MIMEText(body, 'plain'))

# Kirim email
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()  # Enkripsi TLS
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    print("Email berhasil dikirim!")
    server.quit()
except Exception as e:
    print(f"Gagal mengirim email: {e}")
