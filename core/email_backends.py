from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend


class ReadableConsoleEmailBackend(ConsoleEmailBackend):
    def write_message(self, message):
        mime_message = message.message()
        for header in ("From", "To", "Subject"):
            value = mime_message.get(header)
            if value:
                self.stream.write(f"{header}: {value}\n")

        for part in mime_message.walk():
            if part.get_content_type() != "text/plain" or part.get_filename():
                continue

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            charset = part.get_content_charset() or "utf-8"
            self.stream.write("\n")
            self.stream.write(payload.decode(charset))
            self.stream.write("\n")
            self.stream.write("-" * 79)
            self.stream.write("\n")
            return

        super().write_message(message)
