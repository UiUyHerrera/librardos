import sqlite3

import click
from flask.cli import with_appcontext
from sqlalchemy import event
from sqlalchemy.engine import Engine

from reservini.extensions import db


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


@click.command("init-db")
@with_appcontext
def init_db_command():
    db.create_all()
    click.echo("Database ready.")
