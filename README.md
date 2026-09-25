# StockPilot — Smart Inventory & Sales Management System

A practical inventory and sales management web application built with **Python, Flask, SQLite/PostgreSQL, HTML and CSS**.

This project is designed as a portfolio project for a fresher who wants to demonstrate backend development, database design, CRUD operations, authentication, business logic and responsive web development.

## Features

- User registration and secure password hashing
- Login/logout session management
- Dashboard with inventory and sales overview
- Product CRUD: add, edit and delete
- SKU uniqueness validation
- Stock and reorder-level tracking
- Low-stock indicators
- Search products by name/SKU
- Filter products by category
- Sales creation with multiple products
- Automatic stock deduction after a sale
- Stock validation so negative inventory cannot be created through sales
- Invoice details
- Sales history
- Date-filtered sales reports
- CSV sales export
- Responsive layout for desktop, tablet and mobile
- SQLite for simple local development
- PostgreSQL-compatible configuration for production hosting

## Tech stack

- Python 3.12
- Flask
- Flask-SQLAlchemy
- SQLite (local) / PostgreSQL (production)
- HTML5
- CSS3
- Jinja2
- Git & GitHub

## Run locally on Windows

### 1. Open the project

Open this folder in VS Code.

### 2. Create a virtual environment

```powershell
py -m venv venv
```

### 3. Activate it

PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

If Windows blocks PowerShell scripts, use the project's Python directly:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe app.py
```

Or use Command Prompt:

```cmd
venv\Scripts\activate.bat
pip install -r requirements.txt
python app.py
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Optional demo data

```powershell
flask --app app seed
```

Demo login:

- Email: `demo@inventory.local`
- Password: `Demo@12345`

### 6. Start the application

```powershell
python app.py
```

Open:

`http://127.0.0.1:5000`

To make the app accessible to other devices on the same Wi-Fi during development:

```powershell
python -m flask --app app run --host=0.0.0.0 --port=5000
```

Then another device can open:

`http://YOUR-PC-IP:5000`

Windows Firewall may ask for permission. This is only for local-network testing, not public internet hosting.

## Production deployment

The application supports a `DATABASE_URL` environment variable, so it can use PostgreSQL instead of SQLite.

Set:

```text
SECRET_KEY=your-long-random-secret
DATABASE_URL=your-postgresql-connection-string
```

Start with Gunicorn on a Linux host:

```bash
gunicorn app:app
```

For a public production deployment, use HTTPS, a managed PostgreSQL database, a strong secret key, backups and a production hosting provider.

## Database design

### User
Stores application accounts.

### Product
Stores SKU, product name, category, price, stock, reorder level and supplier.

### Sale
Stores invoice number, customer and total amount.

### SaleItem
Connects each sale to its products and stores the quantity and sale-time unit price.

The `SaleItem` table preserves the price used at the time of sale, so changing a product's current price does not rewrite old invoices.

## Main business flow

1. User registers or logs in.
2. User adds products and opening stock.
3. User creates a sale and selects quantities.
4. The application checks available stock.
5. A Sale record and SaleItem records are created.
6. Product stock is reduced automatically.
7. The invoice can be opened and printed.
8. Dashboard and reports reflect the updated sales totals and inventory.
9. CSV export can be used for further analysis.

## Suggested GitHub description

`A production-style Flask inventory and sales management system with authentication, product CRUD, stock tracking, invoicing, reporting and responsive UI.`

## Important portfolio note

Before presenting this as a production deployment, change the default `SECRET_KEY`, use PostgreSQL, enable HTTPS and configure regular database backups.

## Project structure

```text
Smart_Inventory_Sales_Management_System/
├── app.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── .gitignore
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── products.html
│   ├── product_form.html
│   ├── sales.html
│   ├── sale_form.html
│   ├── sale_detail.html
│   └── reports.html
└── static/
    └── css/
        └── style.css
```
