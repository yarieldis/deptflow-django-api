from celery import shared_task

from core.email_utils import dict_to_email


@shared_task(name="deptflow_send_email", ignore_result=True)
def send_emails_task(messages, delivery_mailer="default"):
    """Deliver serialized email messages through the named mailer."""
    from django.core import mail

    connection = mail.mailers.create_connection(delivery_mailer)
    try:
        connection.open()
        for message_dict in messages:
            connection.send_messages([dict_to_email(message_dict)])
    finally:
        connection.close()
