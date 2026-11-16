from email.message import EmailMessage
from email.header import decode_header
from bs4 import BeautifulSoup
import smtplib, ssl, os, imaplib, email, re, html


def html_email_to_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style"]):
        tag.extract()

    for a in soup.find_all("a"):
        if a.get_text(strip=True).startswith(("http://", "https://", "www.")):
            a.extract()

    text = html.unescape(soup.get_text(separator="\n"))

    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = "\n".join(chunk for chunk in chunks if chunk)

    return clean_text

def decode_str(header_value):
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="replace")
        else:
            result += part
    return result

def send_email(sending_user, html_message, subject, recepients, cc=None, bcc=None,):
    msg = EmailMessage()
    msg.add_alternative(html_message, subtype='html')
    msg['Subject'] = subject
    msg['From'] = f'{sending_user.user_name} <{sending_user.user_email}>'
    
    email_recepients = []
    for i, e in enumerate(recepients):
        email_recepients.append("<"+e+">")
    msg['To'] = email_recepients

    if cc != None:
        email_cc = []
        for i, e in enumerate(cc):
            email_cc.append("<"+e+">")
        msg['Cc'] = email_cc

    if bcc != None:
        email_bcc = []
        for i, e in enumerate(bcc):
            email_bcc.append("<"+e+">")
        msg['Bcc'] = email_bcc

    if sending_user.email_type == "gmail":
        smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
        smtpObj.starttls(context=ssl.create_default_context())
        smtpObj.login(sending_user.user_email, sending_user.user_password)  # 16-character app password
        smtpObj.send_message(msg)
        smtpObj.quit()

    elif sending_user.email_type == "proton":
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP("127.0.0.1", 1025) as server: # Connect to local Bridge SMTP server (127.0.0.1 on port 1025)
            server.starttls(context=context)
            server.login(sending_user.user_email, sending_user.user_password) #bridge password
            server.send_message(msg)

def get_inbox(user_inbox_info):

    if user_inbox_info.email_type == "gmail":
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user_inbox_info.user_email, user_inbox_info.user_password) #16-character app password
        mail.select("inbox", readonly=True)

    elif user_inbox_info.email_type == "proton":
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        mail = imaplib.IMAP4("127.0.0.1", 1143) # Connect to local Bridge IMAP server (127.0.0.1 on port 1143)
        mail.starttls(ssl_context=context)
        mail.login(user_inbox_info.user_email, user_inbox_info.user_password) #bridge password

        mail.select("INBOX", readonly=True)

    status, messages = mail.search(None, "UNSEEN") # use unseen to get unread emails only | use all for full inbox
    email_ids = messages[0].split()

    output_emails = []
    for temp_email in email_ids:
        status, msg_data = mail.fetch(temp_email, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                email_info = {
                    "from": decode_str(msg.get("From")),
                    "to": decode_str(msg.get("To")),
                    "cc": decode_str(msg.get("Cc")),
                    "date": msg.get("Date"),
                    "subject": decode_str(msg.get("Subject")),
                    "body_plain": "",
                    "body_html": "",
                    "attachments": []
                }

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))

                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                email_info["attachments"].append(decode_str(filename))
                        
                        elif content_type == "text/plain" and "attachment" not in content_disposition:
                            payload = part.get_payload(decode=True)
                            if payload:
                                email_info["body_plain"] = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                        
                        elif content_type == "text/html" and "attachment" not in content_disposition:
                            payload = part.get_payload(decode=True)
                            if payload:
                                email_info["body_html"] = html_email_to_text(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        email_info["body_plain"] = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")

                output_emails.append(email_info)

    mail.logout()
    return output_emails
