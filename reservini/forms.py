from datetime import UTC, date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from babel.dates import get_day_names, get_timezone_location
from babel.numbers import get_currency_name
from flask_babel import get_locale
from flask_babel import gettext as _
from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    FieldList,
    EmailField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
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
from wtforms.widgets import NumberInput

from reservini.hours import format_ranges, parse_ranges
from reservini.models import OpeningHours

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "MXN", "BRL", "ARS", "COP", "PEN"]
DEFAULT_HOURS = ["09:00-18:00"] * 5 + ["", ""]
TIMEZONES = [
    "Pacific/Honolulu",
    "America/Anchorage",
    "America/Los_Angeles",
    "America/Denver",
    "America/Phoenix",
    "America/Chicago",
    "America/Mexico_City",
    "America/New_York",
    "America/Bogota",
    "America/Lima",
    "America/Caracas",
    "America/La_Paz",
    "America/Santo_Domingo",
    "America/Montevideo",
    "America/Argentina/Buenos_Aires",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Lisbon",
    "Europe/Madrid",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Rome",
    "Africa/Lagos",
    "Europe/Athens",
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Europe/Istanbul",
    "Europe/Moscow",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Bangkok",
    "Asia/Singapore",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Pacific/Auckland",
]


def normalize_email(value):
    return value.strip().lower() if value else value


def normalize_slug(value):
    return value.strip().lower() if value else value


def format_offset(offset):
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "−"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


@lru_cache(maxsize=8)
def timezone_choices(locale_name, day):
    now = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
    zones = []
    for zone in ["UTC", *TIMEZONES]:
        offset = now.astimezone(ZoneInfo(zone)).utcoffset()
        city = get_timezone_location(zone, locale=locale_name, return_city=True).split("/")[-1]
        zones.append((offset, city, zone))
    return [(zone, f"(UTC{format_offset(offset)}) {city}") for offset, city, zone in sorted(zones)]


def currency_label(code, locale):
    name = get_currency_name(code, locale=locale)
    return f"{name[:1].upper()}{name[1:]} ({code})"


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
    hours = FieldList(StringField(validators=[Length(max=200)]), min_entries=7, max_entries=7)

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        locale = get_locale()
        day_names = get_day_names("wide", locale=locale)
        self.timezone.choices = timezone_choices(str(locale), date.today())
        self.currency.choices = [(code, currency_label(code, locale)) for code in CURRENCIES]
        for weekday, entry in enumerate(self.hours):
            entry.label.text = day_names[weekday].capitalize()
            if not self.is_submitted():
                entry.data = format_ranges(business.hours_on(weekday)) if business else DEFAULT_HOURS[weekday]
        self.weekly_hours = {}

    def validate_hours(self, field):
        weekly_hours = {}
        for weekday, entry in enumerate(field):
            try:
                weekly_hours[weekday] = parse_ranges(entry.data)
            except ValueError as error:
                entry.errors.append(str(error))
        if any(entry.errors for entry in field):
            raise ValidationError(_("Check the opening hours."))
        if not any(weekly_hours.values()):
            raise ValidationError(_("Add opening hours for at least one day."))
        self.weekly_hours = weekly_hours

    def apply_to(self, business):
        business.name = self.name.data
        business.slug = self.slug.data
        business.timezone = self.timezone.data
        business.currency = self.currency.data
        business.opening_hours = [
            OpeningHours(weekday=weekday, opens_at=opens, closes_at=closes)
            for weekday, ranges in self.weekly_hours.items()
            for opens, closes in ranges
        ]


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


class BookingForm(FlaskForm):
    slot = RadioField(_l("Time"), validators=[DataRequired(message=_l("Pick a time."))])
    customer_name = StringField(_l("Your name"), validators=[DataRequired(), Length(max=100)])
    customer_email = EmailField(
        _l("Your email"),
        filters=[normalize_email],
        validators=[DataRequired(), Email(), Length(max=255)],
    )
