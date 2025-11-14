#!/usr/bin/env python3
"""Development server for youarecoder Flask app."""
from dotenv import load_dotenv
import os

# Load .env file before importing app
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10081))
    host = os.environ.get('HOST', '127.0.0.1')

    print("=" * 60)
    print("🚀 YouAreCoder Development Server")
    print("=" * 60)
    print(f"📍 Local:  http://{host}:{port}/")
    print(f"🌐 Public: https://mustafa-youarecoder.dev.alkedos.com/")
    print(f"🗄️  Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🔧 Mock Provisioning: {app.config.get('MOCK_PROVISIONING', False)}")
    print("=" * 60)

    app.run(
        host=host,
        port=port,
        debug=True,
        use_reloader=True
    )
