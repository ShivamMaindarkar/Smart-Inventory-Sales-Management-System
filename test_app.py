import os
import tempfile
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app import app, db, User, Product, Sale, SaleItem

class InventoryAppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()
            user = User(name="Test User", email="test@example.com",
                        password_hash="scrypt:32768:8:1$test$dummy")
            # Use real password hash through the app helper instead of checking it here.
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash("password123")
            db.session.add(user)
            db.session.add(Product(sku="T-001", name="Test Product", category="Test",
                                   price=100, stock=10, reorder_level=2, supplier="Test Supplier"))
            db.session.commit()

    def test_login_and_dashboard(self):
        r = self.client.post("/login", data={"email":"test@example.com","password":"password123"}, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Total Products", r.data)

    def test_sale_reduces_stock(self):
        self.client.post("/login", data={"email":"test@example.com","password":"password123"})
        r = self.client.post("/sales/new", data={"customer_name":"Test Customer","qty_1":"3"}, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        with app.app_context():
            p = Product.query.filter_by(sku="T-001").first()
            self.assertEqual(p.stock, 7)
            self.assertEqual(Sale.query.count(), 1)
            self.assertEqual(SaleItem.query.count(), 1)

if __name__ == "__main__":
    unittest.main()
