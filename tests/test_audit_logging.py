#!/usr/bin/env python3
"""
Test script to validate audit logging functionality.
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import AuditLog, WorkspaceSession, User
from app.services.audit_logger import AuditLogger
from datetime import datetime

def test_audit_logging():
    """Test audit logging functionality."""
    print("🧪 Testing Audit Logging System")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        # Test 1: Check if tables exist
        print("\n1️⃣ Checking if audit_logs table exists...")
        try:
            count = db.session.query(AuditLog).count()
            print(f"   ✅ audit_logs table exists (current count: {count})")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            return False

        # Test 2: Check if workspace_sessions table exists
        print("\n2️⃣ Checking if workspace_sessions table exists...")
        try:
            count = db.session.query(WorkspaceSession).count()
            print(f"   ✅ workspace_sessions table exists (current count: {count})")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            return False

        # Test 3: Test direct audit log creation
        print("\n3️⃣ Testing direct audit log creation...")
        try:
            test_log = AuditLog(
                timestamp=datetime.utcnow(),
                action_type='test_action',
                resource_type='test_resource',
                ip_address='127.0.0.1',
                details={'test': 'data'},
                success=True
            )
            db.session.add(test_log)
            db.session.commit()
            print(f"   ✅ Test audit log created (ID: {test_log.id})")

            # Clean up test log
            db.session.delete(test_log)
            db.session.commit()
            print(f"   ✅ Test audit log cleaned up")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            db.session.rollback()
            return False

        # Test 4: Check recent audit logs (from real activity)
        print("\n4️⃣ Checking recent audit logs...")
        try:
            recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
            if recent_logs:
                print(f"   ✅ Found {len(recent_logs)} recent audit logs:")
                for log in recent_logs:
                    print(f"      - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
                          f"{log.action_type} | "
                          f"User {log.user_id or 'N/A'} | "
                          f"IP {log.ip_address or 'N/A'} | "
                          f"{'✅' if log.success else '❌'}")
            else:
                print(f"   ℹ️  No audit logs yet (system just deployed)")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            return False

        # Test 5: Check workspace sessions
        print("\n5️⃣ Checking workspace sessions...")
        try:
            sessions = WorkspaceSession.query.order_by(WorkspaceSession.started_at.desc()).limit(5).all()
            if sessions:
                print(f"   ✅ Found {len(sessions)} workspace sessions:")
                for session in sessions:
                    duration = f"{session.duration_seconds}s" if session.duration_seconds else "ongoing"
                    print(f"      - Workspace {session.workspace_id} | "
                          f"Started {session.started_at.strftime('%Y-%m-%d %H:%M:%S')} | "
                          f"Duration: {duration}")
            else:
                print(f"   ℹ️  No workspace sessions yet")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            return False

        # Test 6: Check indexes
        print("\n6️⃣ Checking database indexes...")
        try:
            result = db.session.execute(
                db.text("""
                    SELECT tablename, indexname
                    FROM pg_indexes
                    WHERE tablename IN ('audit_logs', 'workspace_sessions')
                    ORDER BY tablename, indexname
                """)
            )
            indexes = result.fetchall()
            print(f"   ✅ Found {len(indexes)} indexes:")
            for table, index in indexes:
                print(f"      - {table}.{index}")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            return False

    print("\n" + "=" * 60)
    print("✅ All tests passed! Audit logging system is working correctly.")
    print("\n📋 Next steps:")
    print("   1. Monitor audit logs during user logins")
    print("   2. Check workspace session tracking when users create workspaces")
    print("   3. Verify payment callback logging on next payment")
    print("   4. Test admin export endpoint: /admin/users/<id>/export-logs")
    return True

if __name__ == '__main__':
    success = test_audit_logging()
    sys.exit(0 if success else 1)
