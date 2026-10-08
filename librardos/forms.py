from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Length

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def normalize_email(value):
    return value.strip().lower() if value else value


class RegisterForm(FlaskForm):
    email = EmailField(
        _l("Email"),
        filters=[normalize_email],
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        _l("Password"),
        validators=[
            DataRequired(),
            Length(
                min=PASSWORD_MIN_LENGTH,
                max=PASSWORD_MAX_LENGTH,
                message=_l("Use between %(min)d and %(max)d characters."),
            ),
        ],
    )
    confirm_password = PasswordField(
        _l("Repeat password"),
        validators=[DataRequired(), EqualTo("password", message=_l("Passwords do not match."))],
    )


class LoginForm(FlaskForm):
    email = EmailField(
        _l("Email"),
        filters=[normalize_email],
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        _l("Password"),
        validators=[DataRequired(), Length(max=PASSWORD_MAX_LENGTH)],
    )
    remember_me = BooleanField(_l("Keep me logged in"))
