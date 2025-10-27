"""
WTForms for authentication and workspace management.
"""
import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, ValidationError


def password_strength(form, field):
    """
    Custom validator for password strength.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    """
    password = field.data

    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long')

    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter')

    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter')

    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one digit')

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        raise ValidationError('Password must contain at least one special character (!@#$%^&*etc.)')


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign in')


class RegistrationForm(FlaskForm):
    """Company and user registration form."""
    # Company details
    company_name = StringField('Company Name', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    subdomain = StringField('Subdomain', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[a-z0-9-]+$', message="Only lowercase letters, numbers, and hyphens allowed")
    ])

    # User details
    full_name = StringField('Full Name', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[a-z0-9_]+$', message="Only lowercase letters, numbers, and underscores allowed")
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters"),
        password_strength
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match")
    ])

    submit = SubmitField('Create Account')


class WorkspaceForm(FlaskForm):
    """Workspace creation form."""
    name = StringField('Workspace Name', validators=[
        DataRequired(),
        Length(min=3, max=100),
        Regexp(r'^[a-z0-9-]+$', message="Only lowercase letters, numbers, and hyphens allowed")
    ])
    submit = SubmitField('Create Workspace')
