"""
WTForms for authentication and workspace management.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp


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
        Length(min=8, message="Password must be at least 8 characters")
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match")
    ])

    submit = SubmitField('Register')


class WorkspaceForm(FlaskForm):
    """Workspace creation form."""
    name = StringField('Workspace Name', validators=[
        DataRequired(),
        Length(min=3, max=100),
        Regexp(r'^[a-z0-9-]+$', message="Only lowercase letters, numbers, and hyphens allowed")
    ])
    submit = SubmitField('Create Workspace')
