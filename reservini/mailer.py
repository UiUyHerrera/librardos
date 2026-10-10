import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to, subject, body):
    message = EmailMessage()
    message["From"] = current_app.config["MAIL_SENDER"]
    message["To"] = to
    message["Subject"] = " ".join(subject.split())
    message.set_content(body)

    try:
        deliver(message)
    except (smtplib.SMTPException, OSError):
        current_app.logger.exception("Could not send email: %s", message["Subject"])
        return False
    return True


def deliver(message):
    config = current_app.config
    if not config["MAIL_SERVER"]:
        current_app.logger.info("MAIL_SERVER is not set, skipped email: %s", message["Subject"])
        return

    with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=10) as connection:
        connection.starttls()
        if config["MAIL_USERNAME"]:
            connection.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        connection.send_message(message)
