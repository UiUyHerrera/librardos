import secrets

from sqlalchemy import String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from reservini.extensions import db


class StoredSecret(db.Model):
    __tablename__ = "stored_secrets"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(128))


def stored_secret(name):
    secret = db.session.get(StoredSecret, name)
    if secret is None:
        db.session.add(StoredSecret(name=name, value=secrets.token_hex(32)))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        secret = db.session.get(StoredSecret, name)
    return secret.value
