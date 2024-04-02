from datetime import datetime as dt
import re
import base64
import imaplib
from airflow.hooks.base_hook import BaseHook
import email



class OwnImapHook(BaseHook):
    def __init__(self, imap_conn_id):
        self.imap_conn_id = imap_conn_id
        self.connection = self.get_connection(imap_conn_id)
        self.server = imaplib.IMAP4_SSL(self.connection.host)
        self.server.login(self.connection.login, self.connection.password)


    def get_info_from_mail(self, search_criteria, mailbox='INBOX'):
        letters = dict()
        self.server.select(mailbox)
        search_res, emails = self.server.search(None, search_criteria)
        for n in emails[0].split():
            letter = dict()
            fetch_res, item = self.server.fetch(n,
                                                # '(RFC822)')
                                                 "(BODY.PEEK[])")
            email_body = item[0][1]
            message = email.message_from_bytes(email_body)
            letter['Subject'] = email.header.decode_header(message['Subject'])[0][0].decode()
            letter['From']= re.findall(r"<(.+)>", message['From'] )
            letter['Date'] = dt.strptime(message['date'],
                                     "%a, %d %b %Y %H:%M:%S %z").strftime('%Y-%m-%d %H:%M:%S')
            for part in message.walk():
                if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'plain':
                    text= base64.b64decode(part.get_payload()).decode()  
            letter['Text'] = text
            letters[str(n.decode('UTF-8'))] = letter
            self.server.store(n, '+FLAGS', '\Seen')
        return letters