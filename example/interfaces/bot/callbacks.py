
class SendMail:

    def __init__(self, send_mail: SendMail):
        self._send_mail = send_mail

    def run(self, client: Client):
        self._send_mail.run()
        client.send_message()
