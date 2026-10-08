from datetime import time
from zoneinfo import available_timezones

from babel.dates import get_day_names
from babel.numbers import get_currency_name
from flask_babel import get_locale
from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    EmailField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Regexp,
    ValidationError,
)
from wtforms.widgets import CheckboxInput, ListWidget, NumberInput

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "MXN", "BRL", "ARS", "COP", "PEN"]
TIMEZONES = sorted(
    zone for zone in available_timezones() if "/" in zone and not zone.startswith(("Etc/", "SystemV/"))
)


def normalize_email(value):
    return value.strip().lower() if value else value


def normalize_slug(value):
    return value.strip().lower() if value else value


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


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


class BusinessForm(FlaskForm):
    name = StringField(_l("Business name"), validators=[DataRequired(), Length(max=100)])
    slug = StringField(
        _l("Booking page address"),
        filters=[normalize_slug],
        validators=[
            DataRequired(),
            Length(min=3, max=60),
            Regexp(SLUG_PATTERN, message=_l("Use lowercase letters, numbers and hyphens.")),
        ],
    )
    timezone = SelectField(_l("Time zone"), default="UTC")
    currency = SelectField(_l("Currency"), default="USD")
    opens_at = TimeField(_l("Opens at"), default=time(9, 0), validators=[DataRequired()])
    closes_at = TimeField(_l("Closes at"), default=time(18, 0), validators=[DataRequired()])
    open_weekdays = MultiCheckboxField(
        _l("Open days"),
        coerce=int,
        default=[0, 1, 2, 3, 4],
        validators=[DataRequired(message=_l("Pick at least one day."))],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locale = get_locale()
        day_names = get_day_names("wide", locale=locale)
        self.timezone.choices = ["UTC", *TIMEZONES]
        self.currency.choices = [(code, f"{get_currency_name(code, locale=locale)} ({code})") for code in CURRENCIES]
        self.open_weekdays.choices = [(day, day_names[day].capitalize()) for day in range(7)]

    def validate_closes_at(self, field):
        if self.opens_at.data and field.data and field.data <= self.opens_at.data:
            raise ValidationError(_l("Closing time must be after opening time."))


class ServiceForm(FlaskForm):
    name = StringField(_l("Service name"), validators=[DataRequired(), Length(max=80)])
    duration_minutes = IntegerField(
        _l("Length in minutes"),
        widget=NumberInput(min=5, max=480, step=5),
        validators=[DataRequired(), NumberRange(min=5, max=480)],
    )
    price = DecimalField(
        _l("Price"),
        places=2,
        widget=NumberInput(min=0, step="0.01"),
        validators=[InputRequired(), NumberRange(min=0, max=100000)],
    )
