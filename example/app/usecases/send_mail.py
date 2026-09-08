from pybotx import IncomingMessage


class SendMail:
    def run(self, message: IncomingMessage) -> str:
        # TODO: подключить реальную отправку почты.
        return message.argument
