import base64


def email_to_dict(message) -> dict:
    """Serialize an EmailMessage to a JSON-safe dict for Celery."""
    attachments = []
    for filename, content, mimetype in getattr(message, "attachments", []):
        if isinstance(content, str):
            content = content.encode("utf-8")
        attachments.append(
            (filename, base64.b64encode(content).decode("ascii"), mimetype)
        )

    return {
        "subject": message.subject,
        "body": message.body,
        "from_email": message.from_email,
        "to": list(message.to),
        "cc": list(message.cc),
        "bcc": list(message.bcc),
        "reply_to": list(message.reply_to),
        "headers": dict(message.extra_headers),
        "attachments": attachments,
        "alternatives": list(getattr(message, "alternatives", [])),
    }


def dict_to_email(data: dict):
    """Rebuild an EmailMessage from the serialized dict."""
    from django.core.mail import EmailMultiAlternatives

    message = EmailMultiAlternatives(
        subject=data["subject"],
        body=data["body"],
        from_email=data["from_email"],
        to=data["to"],
        cc=data.get("cc", []),
        bcc=data.get("bcc", []),
        reply_to=data.get("reply_to", []),
        headers=data.get("headers", {}),
    )
    for content, mimetype in data.get("alternatives", []):
        message.attach_alternative(content, mimetype)
    for filename, b64content, mimetype in data.get("attachments", []):
        message.attach(filename, base64.b64decode(b64content), mimetype)
    return message
