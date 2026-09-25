import csv
import io
import os
from datetime import datetime, date
from decimal import Decimal

from flask import Flask, flash, redirect, render_template, request, session, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///" + os.path.join(BASE_DIR, "inventory.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=5)
    supplier = db.Column(db.String(150), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(150), nullable=False, default="Walk-in Customer")
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("SaleItem", backref="sale", cascade="all, delete-orphan")


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    product = db.relationship("Product")


def logged_in():
    return "user_id" in session


def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def money(value):
    return f"₹{Decimal(value or 0):,.2f}"


@app.template_filter("money")
def money_filter(value):
    return money(value)


@app.context_processor
def inject_globals():
    return {
        "current_user": db.session.get(User, session.get("user_id")) if session.get("user_id") else None,
        "today": date.today()
    }


@app.route("/")
def index():
    if logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if logged_in():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter a name, valid email and password of at least 6 characters.", "danger")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("register.html")
        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        flash("Account created successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user.id
        flash("Welcome back!", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    total_products = Product.query.count()
    low_stock = Product.query.filter(Product.stock <= Product.reorder_level).count()
    total_sales = db.session.query(func.coalesce(func.sum(Sale.total), 0)).scalar()
    sales_today = db.session.query(func.coalesce(func.sum(Sale.total), 0)).filter(
        func.date(Sale.created_at) == date.today()
    ).scalar()
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(8).all()
    categories = db.session.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    return render_template(
        "dashboard.html",
        total_products=total_products,
        low_stock=low_stock,
        total_sales=total_sales,
        sales_today=sales_today,
        recent_sales=recent_sales,
        categories=categories,
    )


@app.route("/products")
@login_required
def products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Product.query
    if q:
        query = query.filter(
            db.or_(Product.name.ilike(f"%{q}%"), Product.sku.ilike(f"%{q}%"))
        )
    if category:
        query = query.filter_by(category=category)
    products = query.order_by(Product.created_at.desc()).all()
    categories = [row[0] for row in db.session.query(Product.category).distinct().order_by(Product.category).all()]
    return render_template("products.html", products=products, categories=categories, q=q, category=category)


@app.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        try:
            sku = request.form["sku"].strip().upper()
            name = request.form["name"].strip()
            category = request.form["category"].strip()
            price = Decimal(request.form["price"])
            stock = int(request.form["stock"])
            reorder = int(request.form["reorder_level"])
            supplier = request.form.get("supplier", "").strip()
            if not sku or not name or not category or price < 0 or stock < 0 or reorder < 0:
                raise ValueError
            if Product.query.filter_by(sku=sku).first():
                flash("SKU already exists.", "danger")
                return render_template("product_form.html", product=None)
            db.session.add(Product(
                sku=sku, name=name, category=category, price=price,
                stock=stock, reorder_level=reorder, supplier=supplier
            ))
            db.session.commit()
            flash("Product added successfully.", "success")
            return redirect(url_for("products"))
        except (ValueError, KeyError):
            flash("Please enter valid product details.", "danger")
    return render_template("product_form.html", product=None)


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = db.get_or_404(Product, product_id)
    if request.method == "POST":
        try:
            new_sku = request.form["sku"].strip().upper()
            duplicate = Product.query.filter(Product.sku == new_sku, Product.id != product.id).first()
            if duplicate:
                raise ValueError("SKU already exists")
            product.sku = new_sku
            product.name = request.form["name"].strip()
            product.category = request.form["category"].strip()
            product.price = Decimal(request.form["price"])
            product.stock = int(request.form["stock"])
            product.reorder_level = int(request.form["reorder_level"])
            product.supplier = request.form.get("supplier", "").strip()
            if product.price < 0 or product.stock < 0 or product.reorder_level < 0:
                raise ValueError
            db.session.commit()
            flash("Product updated.", "success")
            return redirect(url_for("products"))
        except (ValueError, KeyError):
            db.session.rollback()
            flash("Please check the entered values.", "danger")
    return render_template("product_form.html", product=product)


@app.post("/products/<int:product_id>/delete")
@login_required
def delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    if SaleItem.query.filter_by(product_id=product.id).first():
        flash("This product has sales history and cannot be deleted. Edit it instead.", "warning")
        return redirect(url_for("products"))
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("products"))


@app.route("/sales")
@login_required
def sales():
    all_sales = Sale.query.order_by(Sale.created_at.desc()).all()
    return render_template("sales.html", sales=all_sales)


@app.route("/sales/new", methods=["GET", "POST"])
@login_required
def new_sale():
    products = Product.query.filter(Product.stock > 0).order_by(Product.name).all()
    if request.method == "POST":
        customer = request.form.get("customer_name", "").strip() or "Walk-in Customer"
        selected = []
        total = Decimal("0.00")
        try:
            for product in products:
                raw_qty = request.form.get(f"qty_{product.id}", "0")
                qty = int(raw_qty or 0)
                if qty < 0:
                    raise ValueError
                if qty > product.stock:
                    flash(f"Not enough stock for {product.name}. Available: {product.stock}.", "danger")
                    return render_template("sale_form.html", products=products)
                if qty:
                    selected.append((product, qty))
                    total += Decimal(product.price) * qty

            if not selected:
                flash("Select at least one product quantity.", "danger")
                return render_template("sale_form.html", products=products)

            invoice = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"
            sale = Sale(invoice_no=invoice, customer_name=customer, total=total)
            db.session.add(sale)
            db.session.flush()

            for product, qty in selected:
                db.session.add(SaleItem(
                    sale_id=sale.id, product_id=product.id,
                    quantity=qty, unit_price=product.price
                ))
                product.stock -= qty

            db.session.commit()
            flash(f"Sale {invoice} recorded successfully.", "success")
            return redirect(url_for("sale_detail", sale_id=sale.id))
        except (ValueError, TypeError):
            db.session.rollback()
            flash("Please enter valid quantities.", "danger")
    return render_template("sale_form.html", products=products)


@app.route("/sales/<int:sale_id>")
@login_required
def sale_detail(sale_id):
    sale = db.get_or_404(Sale, sale_id)
    return render_template("sale_detail.html", sale=sale)


@app.route("/reports")
@login_required
def reports():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    query = Sale.query
    if start:
        try:
            query = query.filter(Sale.created_at >= datetime.fromisoformat(start))
        except ValueError:
            start = ""
    if end:
        try:
            query = query.filter(Sale.created_at < datetime.fromisoformat(end) )
        except ValueError:
            end = ""
    report_sales = query.order_by(Sale.created_at.desc()).all()
    total = sum((Decimal(s.total) for s in report_sales), Decimal("0.00"))
    units = sum(item.quantity for s in report_sales for item in s.items)
    return render_template("reports.html", sales=report_sales, total=total, units=units, start=start, end=end)


@app.route("/export/sales.csv")
@login_required
def export_sales():
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Invoice", "Customer", "Date", "Total"])
    for sale in sales:
        writer.writerow([sale.invoice_no, sale.customer_name, sale.created_at.strftime("%Y-%m-%d %H:%M"), f"{sale.total:.2f}"])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_report.csv"}
    )


@app.cli.command("seed")
def seed():
    """Create demo products and a demo login."""
    db.create_all()
    if not User.query.filter_by(email="demo@inventory.local").first():
        db.session.add(User(
            name="Demo Admin",
            email="demo@inventory.local",
            password_hash=generate_password_hash("Demo@12345")
        ))
    if Product.query.count() == 0:
        demo = [
            ("SKU-1001", "Wireless Mouse", "Accessories", 699, 28, 5, "Tech Supplier"),
            ("SKU-1002", "Mechanical Keyboard", "Accessories", 2499, 14, 4, "Tech Supplier"),
            ("SKU-1003", "USB-C Hub", "Accessories", 1299, 8, 5, "Tech Supplier"),
            ("SKU-1004", "27-inch Monitor", "Monitors", 15999, 6, 3, "Display World"),
            ("SKU-1005", "Laptop Stand", "Office", 1199, 22, 5, "Office Mart"),
            ("SKU-1006", "Webcam", "Accessories", 2199, 11, 4, "Tech Supplier"),
            ("SKU-1007", "Office Chair", "Furniture", 8499, 3, 3, "Office Mart"),
            ("SKU-1008", "Desk Lamp", "Office", 999, 17, 5, "Home Office"),
        ]
        for sku, name, cat, price, stock, reorder, supplier in demo:
            db.session.add(Product(sku=sku, name=name, category=cat, price=price,
                                   stock=stock, reorder_level=reorder, supplier=supplier))
    db.session.commit()
    print("Demo data created. Login: demo@inventory.local / Demo@12345")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
