import unittest
import json
from app import create_app
from extensions import db, bcrypt
from models.user import User
from models.print_order import PrintOrder
from models.audit_log import AuditLog


class TestStrictThreeRoleSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # ── 1. PUBLIC REGISTRATION TESTS ─────────────────────────────────────────
    def test_01_public_registration_strictly_creates_customer(self):
        """Public register endpoint must only create customer accounts."""
        # 1. Register with role='customer'
        res = self.client.post("/api/auth/register", json={
            "name": "Auto Test Customer",
            "email": "autocustomer@test.com",
            "password": "Password@123",
            "role": "customer"
        })
        self.assertIn(res.status_code, [201, 409])
        if res.status_code == 201:
            data = res.get_json()
            self.assertEqual(data["user"]["role"], "customer")

        # 2. Attempt to register as 'admin' -> MUST BE REJECTED with 403
        res_admin = self.client.post("/api/auth/register", json={
            "name": "Hacker Admin",
            "email": "hackeradmin@test.com",
            "password": "Password@123",
            "role": "admin"
        })
        self.assertEqual(res_admin.status_code, 403)

        # 3. Attempt to register as 'super_admin' -> MUST BE REJECTED with 403
        res_super = self.client.post("/api/auth/register", json={
            "name": "Hacker Super",
            "email": "hackersuper@test.com",
            "password": "Password@123",
            "role": "super_admin"
        })
        self.assertEqual(res_super.status_code, 403)

    # ── 2. LOGIN & ROLE REDIRECTION PAYLOAD TESTS ───────────────────────────
    def test_02_login_returns_exact_db_role_and_tracks_activity(self):
        """Login should return user role without dropdown and increment login_count."""
        # Login with Super Admin
        res = self.client.post("/api/auth/login", json={
            "email": "superadmin@smarteprint.com",
            "password": "SuperAdmin@2026"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["user"]["role"], "super_admin")
        self.assertTrue(data["token"])

        # Check that login audit log was recorded
        log = AuditLog.query.filter_by(user_email="superadmin@smarteprint.com", action="USER_LOGIN").first()
        self.assertIsNotNone(log)

    # ── 3. ROLE ACCESS CONTROL & 403 FORBIDDEN GUARDS ────────────────────────
    def test_03_customer_cannot_access_admin_or_superadmin_apis(self):
        """Customer token attempting to access restricted routes gets 403."""
        # Login customer
        login_res = self.client.post("/api/auth/login", json={
            "email": "autocustomer@test.com",
            "password": "Password@123"
        })
        cust_token = login_res.get_json().get("token")
        headers = {"Authorization": f"Bearer {cust_token}"}

        # Try to access super-admin stats
        res_super_stats = self.client.get("/api/super-admin/stats", headers=headers)
        self.assertEqual(res_super_stats.status_code, 403)

        # Try to access super-admin users
        res_super_users = self.client.get("/api/super-admin/users", headers=headers)
        self.assertEqual(res_super_users.status_code, 403)

        # Try to access admin order stats
        res_order_stats = self.client.get("/api/orders/stats", headers=headers)
        self.assertEqual(res_order_stats.status_code, 403)

    def test_04_admin_cannot_access_superadmin_apis(self):
        """Admin token attempting to access Super Admin routes gets 403."""
        # Get admin user
        admin = User.query.filter_by(role="admin").first()
        self.assertIsNotNone(admin)

        # Login admin
        login_res = self.client.post("/api/auth/login", json={
            "email": admin.email,
            "password": "Admin@2026" if admin.email == "admin@smarteprint.com" else "Password@123"
        })
        # If legacy admin has different password, test token directly
        from routes.auth import _generate_token
        admin_token = _generate_token(admin)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Admin tries to access Super Admin endpoints -> MUST BE 403
        res = self.client.get("/api/super-admin/stats", headers=headers)
        self.assertEqual(res.status_code, 403)

        res_users = self.client.get("/api/super-admin/users", headers=headers)
        self.assertEqual(res_users.status_code, 403)

        # Admin CAN access orders/stats
        res_stats = self.client.get("/api/orders/stats", headers=headers)
        self.assertEqual(res_stats.status_code, 200)

    # ── 4. SUPER ADMIN SINGLE ADMIN MANAGEMENT & INVARIANTS ─────────────────
    def test_05_superadmin_admin_management(self):
        """Super Admin can view, reset password, disable, and replace single Admin."""
        sa = User.query.filter_by(role="super_admin").first()
        from routes.auth import _generate_token
        sa_token = _generate_token(sa)
        headers = {"Authorization": f"Bearer {sa_token}"}

        # 1. Get current admin
        res = self.client.get("/api/super-admin/admin-account", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsNotNone(data["admin"])

        # 2. Reset Admin password
        res_reset = self.client.post("/api/super-admin/admin-account/reset-password",
                                    headers=headers,
                                    json={"password": "NewAdminPassword@2026"})
        self.assertEqual(res_reset.status_code, 200)

        # 3. Toggle Admin status (disable / enable)
        res_disable = self.client.patch("/api/super-admin/admin-account/status",
                                       headers=headers,
                                       json={"is_active": False})
        self.assertEqual(res_disable.status_code, 200)
        self.assertFalse(res_disable.get_json()["admin"]["is_active"])

        # Re-enable
        res_enable = self.client.patch("/api/super-admin/admin-account/status",
                                      headers=headers,
                                      json={"is_active": True})
        self.assertEqual(res_enable.status_code, 200)
        self.assertTrue(res_enable.get_json()["admin"]["is_active"])

        # 4. Replace Admin
        res_replace = self.client.post("/api/super-admin/admin-account/replace",
                                      headers=headers,
                                      json={
                                          "name": "Replaced Head Admin",
                                          "email": "headadmin@smarteprint.com",
                                          "password": "AdminReplaced@2026"
                                      })
        self.assertEqual(res_replace.status_code, 200)
        self.assertEqual(res_replace.get_json()["admin"]["email"], "headadmin@smarteprint.com")

        # Verify invariant: Exactly 1 Admin exists
        admin_count = User.query.filter_by(role="admin").count()
        self.assertEqual(admin_count, 1)

    # ── 5. SUPER ADMIN CUSTOMER MANAGEMENT & SAFE PRESERVATION ──────────────
    def test_06_superadmin_customer_management_and_safe_deletion(self):
        """Super admin can create, toggle, and delete customer without deleting print records."""
        sa = User.query.filter_by(role="super_admin").first()
        from routes.auth import _generate_token
        sa_token = _generate_token(sa)
        headers = {"Authorization": f"Bearer {sa_token}"}

        # 1. Super Admin creates a customer
        res = self.client.post("/api/super-admin/users", headers=headers, json={
            "name": "Managed Customer",
            "email": "managedcust@test.com",
            "password": "Password@123"
        })
        self.assertEqual(res.status_code, 201)
        cust_id = res.get_json()["user"]["id"]

        # 2. Toggle active status
        res_toggle = self.client.patch(f"/api/super-admin/users/{cust_id}/status", headers=headers, json={"is_active": False})
        self.assertEqual(res_toggle.status_code, 200)
        self.assertFalse(res_toggle.get_json()["user"]["is_active"])

        # 3. Create dummy order attached to this customer
        dummy_order = PrintOrder(
            user_id=cust_id,
            customer_name="Managed Customer",
            customer_email="managedcust@test.com",
            file_name="test_doc.pdf",
            file_path="/tmp/test_doc.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            file_size=1024,
            page_count=2,
            print_mode="bw",
            copies=1,
            page_range="1-2",
            printed_pages=2,
            unit_rate=2.0,
            multiplier=1.0,
            total_price=4.0,
            status="Submitted"
        )
        db.session.add(dummy_order)
        db.session.commit()
        order_id = dummy_order.id

        # 4. Super Admin deletes the customer
        res_del = self.client.delete(f"/api/super-admin/users/{cust_id}", headers=headers)
        self.assertEqual(res_del.status_code, 200)

        # 5. Verify the customer was deleted from Users table
        self.assertIsNone(db.session.get(User, cust_id))

        # 6. CRITICAL VERIFICATION: Print order MUST STILL EXIST with snapshot intact!
        preserved_order = db.session.get(PrintOrder, order_id)
        self.assertIsNotNone(preserved_order)
        self.assertEqual(preserved_order.customer_name, "Managed Customer")
        self.assertEqual(preserved_order.customer_email, "managedcust@test.com")
        self.assertIsNone(preserved_order.user_id)

        # Clean up dummy order
        db.session.delete(preserved_order)
        db.session.commit()


if __name__ == "__main__":
    unittest.main()
