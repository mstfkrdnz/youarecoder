"""
Legal routes (Terms of Service, Privacy Policy).
"""
from flask import Blueprint, render_template

bp = Blueprint('legal', __name__, url_prefix='/legal')


@bp.route('/terms-tr')
def terms_tr():
    """Terms of Service in Turkish."""
    return render_template('legal/terms_tr.html')


@bp.route('/terms-en')
def terms_en():
    """Terms of Service in English."""
    return render_template('legal/terms_en.html')


@bp.route('/privacy-tr')
def privacy_tr():
    """Privacy Policy in Turkish."""
    return render_template('legal/privacy_tr.html')


@bp.route('/privacy-en')
def privacy_en():
    """Privacy Policy in English."""
    return render_template('legal/privacy_en.html')
