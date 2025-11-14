#!/usr/bin/env python3
"""Initialize database tables for youarecoder development environment."""
from dotenv import load_dotenv
load_dotenv()

from app import create_app, db

app = create_app('development')

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("✅ Database tables created successfully!")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
