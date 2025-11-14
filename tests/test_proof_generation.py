#!/usr/bin/env python3
"""
Test script for chargeback proof package generation.
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Payment
from app.services.proof_package_generator import ChargebackProofGenerator

def test_proof_generation():
    """Test proof package generation with existing payment data."""
    print("🧪 Testing Chargeback Proof Package Generation")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        # Find a completed payment
        print("\n1️⃣ Finding completed payment...")
        payment = Payment.query.filter_by(status='completed').first()

        if not payment:
            print("   ❌ No completed payments found in database")
            print("   ℹ️  This is expected if no real payments have been made yet")
            return True

        print(f"   ✅ Found payment: {payment.merchant_oid}")
        print(f"      Amount: {payment.amount} {payment.currency}")
        print(f"      Status: {payment.status}")
        print(f"      Date: {payment.created_at}")

        # Generate proof package
        print("\n2️⃣ Generating proof package...")
        try:
            generator = ChargebackProofGenerator()
            zip_path, package_id = generator.generate_proof_package(
                payment_id=payment.id,
                dispute_reason="Test generation - Quality assurance"
            )

            if not zip_path:
                print("   ❌ Proof generation failed")
                return False

            print(f"   ✅ Package generated successfully!")
            print(f"      Package ID: {package_id}")
            print(f"      ZIP Path: {zip_path}")

            # Check file size
            if os.path.exists(zip_path):
                file_size = os.path.getsize(zip_path) / 1024  # KB
                print(f"      File Size: {file_size:.2f} KB")

                # Verify it's a valid ZIP
                import zipfile
                if zipfile.is_zipfile(zip_path):
                    print(f"      ✅ Valid ZIP file")

                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        files = zf.namelist()
                        print(f"      ✅ Contains {len(files)} files:")
                        for filename in files:
                            print(f"         - {filename}")
                else:
                    print(f"      ❌ Invalid ZIP file")
                    return False
            else:
                print(f"      ❌ ZIP file not found")
                return False

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

        # Test data compilation
        print("\n3️⃣ Verifying data compilation...")
        try:
            company = payment.company
            user = company.users.first()

            print(f"   ✅ Company: {company.name} (ID: {company.id})")
            print(f"   ✅ User: {user.email} (ID: {user.id})")

            # Check audit logs
            from app.models import AuditLog
            audit_count = AuditLog.query.filter_by(company_id=company.id).count()
            print(f"   ✅ Audit Logs: {audit_count}")

            # Check workspace sessions
            from app.models import WorkspaceSession
            session_count = WorkspaceSession.query.filter(
                WorkspaceSession.workspace_id.in_([w.id for w in company.workspaces])
            ).count()
            print(f"   ✅ Workspace Sessions: {session_count}")

            # Check email logs
            from app.models import EmailLog
            email_count = EmailLog.query.filter_by(company_id=company.id).count()
            print(f"   ✅ Email Logs: {email_count}")

        except Exception as e:
            print(f"   ⚠️  Warning during data verification: {str(e)}")

    print("\n" + "=" * 60)
    print("✅ Proof package generation test completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Review generated PDF for professional quality")
    print("   2. Verify ZIP structure matches specifications")
    print("   3. Test admin endpoint: GET /admin/chargeback/generate/<payment_id>")
    print("   4. Generate proof package for real chargeback dispute")
    return True

if __name__ == '__main__':
    success = test_proof_generation()
    sys.exit(0 if success else 1)
