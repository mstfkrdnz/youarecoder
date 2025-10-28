"""
Legal routes (Terms of Service, Privacy Policy, Contact).
"""
from flask import Blueprint, render_template

bp = Blueprint('legal', __name__, url_prefix='/legal')


@bp.route('/terms')
def terms():
    """Terms of Service - Default English."""
    return render_template('legal/terms_en.html')


@bp.route('/terms-tr')
def terms_tr():
    """Terms of Service in Turkish."""
    return render_template('legal/terms_tr.html')


@bp.route('/terms-en')
def terms_en():
    """Terms of Service in English."""
    return render_template('legal/terms_en.html')


@bp.route('/privacy')
def privacy():
    """Privacy Policy - Default English."""
    return render_template('legal/privacy_en.html')


@bp.route('/privacy-tr')
def privacy_tr():
    """Privacy Policy in Turkish."""
    return render_template('legal/privacy_tr.html')


@bp.route('/privacy-en')
def privacy_en():
    """Privacy Policy in English."""
    return render_template('legal/privacy_en.html')


@bp.route('/contact')
def contact():
    """Contact page - Default English."""
    return render_template('legal/contact_en.html')


@bp.route('/contact-tr')
def contact_tr():
    """Contact page in Turkish."""
    return render_template('legal/contact_tr.html')


@bp.route('/contact-en')
def contact_en():
    """Contact page in English."""
    return render_template('legal/contact_en.html')
