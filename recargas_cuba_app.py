from flask import Flask, request, render_template_string, redirect, url_for, session, flash, abort
from datetime import datetime
from functools import wraps
from pathlib import Path
import sqlite3

app = Flask(__name__)
app.secret_key = "cambia-esta-clave-secreta-por-una-mas-segura"

PROMO_START = "10 de marzo"
PROMO_END = "15 de marzo"
PRECIO_RECARGA = "14 500 CUP"
DB_PATH = Path(__file__).with_name("recargas.db")


# -----------------------------
# Base de datos
# -----------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            message TEXT,
            status TEXT NOT NULL DEFAULT 'Pendiente',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    admin_email = "admin@recargas.local"
    existing_admin = conn.execute(
        "SELECT id FROM users WHERE email = ?", (admin_email,)
    ).fetchone()

    if not existing_admin:
        conn.execute(
            """
            INSERT INTO users (name, email, password, is_admin, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Administrador",
                admin_email,
                "admin123",
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# Helpers de autenticación
# -----------------------------
def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login"))
        if not user["is_admin"]:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


# -----------------------------
# Plantilla base
# -----------------------------
BASE_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root {
      --bg: #f8fafc;
      --bg-2: #eef2ff;
      --card: rgba(255,255,255,0.92);
      --card-strong: rgba(255,255,255,0.12);
      --text: #0f172a;
      --muted: #475569;
      --accent: #2563eb;
      --accent-2: #0ea5e9;
      --border: rgba(15,23,42,0.10);
      --shadow: 0 18px 40px rgba(15,23,42,0.10);
      --danger: #dc2626;
      --warning: #f59e0b;
      --success: #22c55e;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top right, rgba(37,99,235,0.10), transparent 22%),
        radial-gradient(circle at top left, rgba(14,165,233,0.10), transparent 20%),
        linear-gradient(180deg, var(--bg-2) 0%, var(--bg) 100%);
      min-height: 100vh;
    }

    a { color: inherit; text-decoration: none; }
    .container { width: min(1120px, 92%); margin: 0 auto; }

    .nav {
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(10px);
      background: rgba(255,255,255,0.86);
      border-bottom: 1px solid rgba(15,23,42,0.08);
    }

    .nav-inner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 0;
      gap: 14px;
    }

    .brand {
      font-weight: 800;
      font-size: 1.08rem;
      letter-spacing: 0.2px;
    }

    .nav-links {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 14px;
      padding: 11px 16px;
      font-weight: 700;
      border: 1px solid transparent;
      cursor: pointer;
      transition: .18s ease;
    }

    .btn:hover { transform: translateY(-1px); }
    .btn-primary {
      background: linear-gradient(135deg, var(--accent), #16a34a);
      color: var(--text);
      box-shadow: var(--shadow);
    }
    .btn-secondary {
      background: rgba(255,255,255,0.88);
      border-color: var(--border);
      color: var(--text);
    }
    .btn-danger {
      background: rgba(239,68,68,0.08);
      border-color: rgba(239,68,68,0.25);
      color: #b91c1c;
    }

    .hero {
      padding: 68px 0 36px;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 28px;
      align-items: center;
    }

    .badge {
      display: inline-block;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(37,99,235,0.10);
      border: 1px solid rgba(37,99,235,0.18);
      color: #1d4ed8;
      font-size: 0.88rem;
      margin-bottom: 16px;
      font-weight: 700;
    }

    h1 {
      margin: 0 0 12px;
      font-size: clamp(2rem, 5vw, 4rem);
      line-height: 1.05;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 1.8rem;
    }

    .subtitle {
      color: var(--muted);
      font-size: 1.06rem;
      line-height: 1.65;
      margin-bottom: 22px;
    }

    .hero-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 22px;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }

    .price-card {
      padding: 26px;
      background: linear-gradient(180deg, rgba(255,255,255,0.11), rgba(255,255,255,0.07));
    }

    .price-kicker {
      color: #2563eb;
      font-weight: 700;
      font-size: 0.92rem;
      margin-bottom: 8px;
    }

    .price {
      font-size: clamp(2rem, 4vw, 3rem);
      font-weight: 800;
      margin: 8px 0;
    }

    .promo-box {
      margin-top: 16px;
      padding: 18px;
      border-radius: 18px;
      background: rgba(37,99,235,0.06);
      border: 1px solid rgba(37,99,235,0.15);
    }

    .promo-box ul {
      margin: 10px 0 0 18px;
      padding: 0;
      color: var(--muted);
      line-height: 1.7;
    }

    .section {
      padding: 16px 0 54px;
    }

    .grid-3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(0,1fr));
      gap: 18px;
    }

    .feature, .panel, .form-card, .auth-card {
      padding: 24px;
    }

    .feature h3 {
      margin: 0 0 8px;
      font-size: 1.12rem;
    }

    .feature p, .muted {
      color: var(--muted);
      line-height: 1.7;
    }

    .page-wrap {
      padding: 40px 0 60px;
    }

    .auth-shell {
      min-height: calc(100vh - 80px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 40px 0;
    }

    .auth-card {
  width: min(460px, 92vw);
  padding: 28px;
    }

    form {
      display: grid;
      gap: 14px;
    }

    label {
      display: block;
      font-size: 0.92rem;
      margin-bottom: 6px;
      font-weight: 700;
      color: #e2e8f0;
    }

    input, textarea, select {
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.95);
  color: var(--text);
  padding: 14px 15px;
  font-size: 1rem;
  outline: none;
    }

    textarea {
      min-height: 110px;
      resize: vertical;
    }

    input:focus, textarea:focus, select:focus {
      border-color: rgba(56,189,248,0.55);
      box-shadow: 0 0 0 4px rgba(56,189,248,0.10);
    }

    .flash-wrap {
      display: grid;
      gap: 10px;
      margin-bottom: 18px;
    }

    .flash {
      padding: 13px 15px;
      border-radius: 14px;
      font-weight: 700;
      border: 1px solid transparent;
    }

    .flash-success {
      background: rgba(34,197,94,0.15);
      border-color: rgba(34,197,94,0.26);
      color: #dcfce7;
    }

    .flash-error {
      background: rgba(239,68,68,0.15);
      border-color: rgba(239,68,68,0.26);
      color: #fecaca;
    }

    .flash-info {
      background: rgba(56,189,248,0.12);
      border-color: rgba(56,189,248,0.24);
      color: #dbeafe;
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0,1fr));
      gap: 16px;
      margin-bottom: 22px;
    }

    .stat {
      padding: 20px;
    }

    .stat .label {
      color: var(--muted);
      font-size: 0.92rem;
      margin-bottom: 8px;
    }

    .stat .value {
      font-size: 1.8rem;
      font-weight: 800;
    }

    .table-card {
      overflow: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: rgba(248,250,252,0.92);
    }

    th, td {
      padding: 14px 14px;
      text-align: left;
      border-bottom: 1px solid rgba(15,23,42,0.08);
      vertical-align: top;
    }

    th {
      color: #e2e8f0;
      font-size: 0.92rem;
      background: rgba(241,245,249,0.95);
    }

    td {
      color: var(--muted);
      font-size: 0.96rem;
    }

    .status {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 800;
      white-space: nowrap;
    }

    .status-pendiente {
      background: rgba(245,158,11,0.15);
      color: #fde68a;
      border: 1px solid rgba(245,158,11,0.22);
    }

    .status-procesando {
      background: rgba(56,189,248,0.15);
      color: #bfdbfe;
      border: 1px solid rgba(56,189,248,0.22);
    }

    .status-completado {
      background: rgba(34,197,94,0.15);
      color: #bbf7d0;
      border: 1px solid rgba(34,197,94,0.22);
    }

    .status-cancelado {
      background: rgba(239,68,68,0.15);
      color: #fecaca;
      border: 1px solid rgba(239,68,68,0.22);
    }

    .top-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .footer {
      padding: 28px 0 50px;
      color: var(--muted);
      border-top: 1px solid rgba(255,255,255,0.08);
      margin-top: 18px;
    }

    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
    }

    @media (max-width: 980px) {
  .hero-grid,
  .grid-3,
  .stats {
    grid-template-columns: 1fr;
    }

  .nav-inner {
    flex-direction: column;
    align-items: stretch;
    }

  .brand {
    text-align: center;
    }

  .nav-links {
    justify-content: center;
    width: 100%;
    }

  .hero {
    padding: 34px 0 24px;
    }

  h1 {
    font-size: clamp(2rem, 10vw, 3.2rem);
    }

  .hero-actions {
    flex-direction: column;
    }

  .hero-actions .btn {
    width: 100%;
    }

  .price-card {
    padding: 20px;
    }
  }

    @media (max-width: 640px) {
  .auth-shell {
    padding: 24px 0 40px;
    min-height: auto;
  }

  .auth-card {
    width: min(94vw, 100%);
    padding: 22px;
    border-radius: 20px;
  }

  .auth-card h2 {
    font-size: 2.2rem;
    line-height: 1.05;
  }

  .auth-card .btn {
    width: 100%;
  }

  .auth-card form {
    gap: 12px;
  }

  .auth-card input {
    padding: 13px 14px;
  }
}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="container nav-inner">
      <div class="brand"><a href="{{ url_for('home') }}">Recargas a Cuba</a></div>
      <div class="nav-links">
        {% if user %}
          {% if user['is_admin'] %}
            <a class="btn btn-secondary" href="{{ url_for('admin_dashboard') }}">Dashboard admin</a>
          {% else %}
            <a class="btn btn-secondary" href="{{ url_for('dashboard') }}">Mi cuenta</a>
            <a class="btn btn-secondary" href="{{ url_for('new_order') }}">Nuevo pedido</a>
          {% endif %}
          <a class="btn btn-danger" href="{{ url_for('logout') }}">Salir</a>
        {% else %}
          <a class="btn btn-secondary" href="{{ url_for('login') }}">Entrar</a>
          <a class="btn btn-primary" href="{{ url_for('register') }}">Crear cuenta</a>
        {% endif %}
      </div>
    </div>
  </nav>

  {% if not hide_container %}<div class="container">{% endif %}
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="flash-wrap" style="padding-top: 18px;">
          {% for category, message in messages %}
            <div class="flash flash-{{ category }}">{{ message }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
  {% if not hide_container %}</div>{% endif %}

  {{ content|safe }}
</body>
</html>
"""


def render_page(content, title="Recargas a Cuba", user=None, hide_container=False, **context):
    rendered_content = render_template_string(
        content,
        user=user,
        **context,
    )
    return render_template_string(
        BASE_HTML,
        content=rendered_content,
        title=title,
        user=user,
        hide_container=hide_container,
    )


# -----------------------------
# Landing
# -----------------------------
@app.route("/")
def home():
    user = current_user()
    content = """
    <header class="hero">
      <div class="container hero-grid">
        <div>
          <div class="badge">Servicios disponibles en la plataforma</div>
          <h1>Recargas a Cuba y más servicios en un solo lugar.</h1>
          <p class="subtitle">
            Tus clientes pueden registrarse, entrar a su cuenta y revisar el historial de pedidos.
            También puedes mostrar varios servicios como recargas, compra de USDT, envíos de paquetes y más.
          </p>

          <div class="hero-actions">
            {% if user %}
              {% if user['is_admin'] %}
                <a class="btn btn-primary" href="{{ url_for('admin_dashboard') }}">Ir al dashboard admin</a>
              {% else %}
                <a class="btn btn-primary" href="{{ url_for('new_order') }}">Hacer pedido</a>
              {% endif %}
            {% else %}
              <a class="btn btn-primary" href="{{ url_for('register') }}">Crear cuenta</a>
              <a class="btn btn-secondary" href="{{ url_for('login') }}">Iniciar sesión</a>
            {% endif %}
          </div>
        </div>

        <div class="card price-card">
          <div class="price-kicker">PROMOCIÓN DEL {{ promo_start }} AL {{ promo_end }}</div>
          <div class="price">{{ precio }}</div>
          <div class="muted">Recarga promocional disponible para clientes en Cuba durante las fechas activas.</div>

          <div class="promo-box">
            <strong>Bonificación actual</strong>
            <ul>
              <li>25GB de navegación válidos para todas las redes.</li>
              <li>Datos ilimitados desde las 12:00 a.m. hasta las 7:00 a.m.</li>
              <li>Aplica a recargas entre 600 CUP y 1250 CUP.</li>
            </ul>
          </div>
        </div>
      </div>
    </header>

    <section class="section">
      <div class="container">
        <div class="top-row">
          <div>
            <h2>Nuestros servicios</h2>
            <p class="muted">Puedes usar estas tarjetas como menú principal de servicios.</p>
          </div>
        </div>

        <div class="grid-3">
          <div class="card feature">
            <h3>Recargas</h3>
            <p>Recargas promocionales y pedidos organizados desde la cuenta del usuario.</p>
          </div>
          <div class="card feature">
            <h3>Compra de USDT</h3>
            <p>Espacio para publicar compra y venta de USDT.</p>
          </div>
          <div class="card feature">
            <h3>Envíos de paquetes</h3>
            <p>Servicio para paquetería, encargos y entregas a Cuba.</p>
          </div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="container">Plataforma de servicios · {{ year }}</div>
    </footer>
    """
    return render_page(
        content,
        title="Recargas a Cuba",
        user=user,
        promo_start=PROMO_START,
        promo_end=PROMO_END,
        precio=PRECIO_RECARGA,
        year=datetime.now().year,
    )


# -----------------------------
# Registro / login / logout
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            flash("Completa todos los campos.", "error")
        elif len(password) < 4:
            flash("La contraseña debe tener al menos 4 caracteres.", "error")
        else:
            conn = get_db()
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                conn.close()
                flash("Ese correo ya está registrado.", "error")
            else:
                conn.execute(
                    """
                    INSERT INTO users (name, email, password, is_admin, created_at)
                    VALUES (?, ?, ?, 0, ?)
                    """,
                    (name, email, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
                conn.commit()
                user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                conn.close()
                session["user_id"] = user["id"]
                flash("Cuenta creada correctamente.", "success")
                return redirect(url_for("dashboard"))

    content = """
    <div class="auth-shell">
      <div class="card auth-card">
        <h2>Crear cuenta</h2>
        <p class="muted">Regístrate para hacer pedidos y revisar tu historial.</p>
        <form method="post">
          <div>
            <label>Nombre</label>
            <input type="text" name="name" required>
          </div>
          <div>
            <label>Correo electrónico</label>
            <input type="email" name="email" required>
          </div>
          <div>
            <label>Contraseña</label>
            <input type="password" name="password" required>
          </div>
          <button class="btn btn-primary" type="submit">Crear cuenta</button>
        </form>
        <p class="muted">¿Ya tienes cuenta? <a href="{{ url_for('login') }}"><strong>Inicia sesión</strong></a></p>
      </div>
    </div>
    """
    return render_page(content, title="Crear cuenta", user=None, hide_container=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        user = current_user()
        if user["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password),
        ).fetchone()
        conn.close()

        if not user:
            flash("Correo o contraseña incorrectos.", "error")
        else:
            session["user_id"] = user["id"]
            flash("Sesión iniciada correctamente.", "success")
            if user["is_admin"]:
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard"))

    content = """
<div class="auth-shell">
  <div class="card auth-card">
    <h2>Iniciar sesión</h2>
    <p class="muted">Entra a tu cuenta para revisar o crear pedidos.</p>
    <form method="post">
      <div>
        <label>Correo electrónico</label>
        <input type="email" name="email" required>
      </div>
      <div>
        <label>Contraseña</label>
        <input type="password" name="password" required>
      </div>
      <button class="btn btn-primary" type="submit">Entrar</button>
    </form>
    <p class="muted">¿No tienes cuenta? <a href="{{ url_for('register') }}"><strong>Créala aquí</strong></a></p>
  </div>
</div>
"""
    return render_page(content, title="Iniciar sesión", user=None, hide_container=True)


@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("home"))


# -----------------------------
# Usuario: dashboard y pedidos
# -----------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user["is_admin"]:
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    orders = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC",
        (user["id"],),
    ).fetchall()
    conn.close()

    total_orders = len(orders)
    pending = sum(1 for o in orders if o["status"] == "Pendiente")
    processing = sum(1 for o in orders if o["status"] == "Procesando")
    completed = sum(1 for o in orders if o["status"] == "Completado")

    content = """
    <div class="page-wrap">
      <div class="container">
        <div class="top-row">
          <div>
            <h2>Mi cuenta</h2>
            <p class="muted">Bienvenido, {{ user['name'] }}. Aquí puedes revisar todos tus pedidos.</p>
          </div>
          <a class="btn btn-primary" href="{{ url_for('new_order') }}">Crear nuevo pedido</a>
        </div>

        <div class="stats">
          <div class="card stat"><div class="label">Pedidos totales</div><div class="value">{{ total_orders }}</div></div>
          <div class="card stat"><div class="label">Pendientes</div><div class="value">{{ pending }}</div></div>
          <div class="card stat"><div class="label">Procesando</div><div class="value">{{ processing }}</div></div>
          <div class="card stat"><div class="label">Completados</div><div class="value">{{ completed }}</div></div>
        </div>

        <div class="card table-card">
          {% if orders %}
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Número</th>
                <th>Mensaje</th>
                <th>Estado</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {% for order in orders %}
              <tr>
                <td data-label="ID">#{{ order['id'] }}</td>
                <td data-label="Número">{{ order['phone_number'] }}</td>
                <td data-label="Mensaje">{{ order['message'] or 'Sin mensaje' }}</td>
                <td data-label="Estado">
                  <span class="status status-{{ order['status'].lower()|replace('á','a')|replace('é','e')|replace('í','i')|replace('ó','o')|replace('ú','u') }}">{{ order['status'] }}</span>
                </td>
                <td data-label="Fecha">{{ order['created_at'] }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
          {% else %}
            <div class="empty">Todavía no tienes pedidos creados.</div>
          {% endif %}
        </div>
      </div>
    </div>
    """
    return render_page(
        content,
        title="Mi cuenta",
        user=user,
        orders=orders,
        total_orders=total_orders,
        pending=pending,
        processing=processing,
        completed=completed,
    )


@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    user = current_user()
    if user["is_admin"]:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        message = request.form.get("message", "").strip()

        if not customer_name or not phone_number:
            flash("Completa los campos obligatorios.", "error")
        else:
            conn = get_db()
            conn.execute(
                """
                INSERT INTO orders (user_id, customer_name, phone_number, message, status, created_at)
                VALUES (?, ?, ?, ?, 'Pendiente', ?)
                """,
                (
                    user["id"],
                    customer_name,
                    phone_number,
                    message,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            conn.close()
            flash("Pedido creado correctamente.", "success")
            return redirect(url_for("dashboard"))

    content = """
    <div class="page-wrap">
      <div class="container" style="max-width:760px;">
        <div class="card form-card">
          <h2>Nuevo pedido</h2>
          <p class="muted">Crea una recarga y luego podrás seguir el estado desde tu cuenta.</p>
          <form method="post">
            <div>
              <label>Nombre del cliente</label>
              <input type="text" name="customer_name" required>
            </div>
            <div>
              <label>Número a recargar</label>
              <input type="text" name="phone_number" placeholder="53XXXXXXXX" required>
            </div>
            <div>
              <label>Mensaje adicional</label>
              <textarea name="message" placeholder="Ej: aplicar promo actual"></textarea>
            </div>
            <button class="btn btn-primary" type="submit">Guardar pedido</button>
          </form>
        </div>
      </div>
    </div>
    """
    return render_page(content, title="Nuevo pedido", user=user)


# -----------------------------
# Admin dashboard
# -----------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    user = current_user()
    conn = get_db()
    orders = conn.execute(
        """
        SELECT orders.*, users.name AS user_name, users.email AS user_email
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.id DESC
        """
    ).fetchall()
    users = conn.execute(
        "SELECT * FROM users ORDER BY id DESC"
    ).fetchall()
    conn.close()

    total_orders = len(orders)
    total_users = sum(1 for u in users if not u["is_admin"])
    pending = sum(1 for o in orders if o["status"] == "Pendiente")
    completed = sum(1 for o in orders if o["status"] == "Completado")

    content = """
    <div class="page-wrap">
      <div class="container">
        <div class="top-row">
          <div>
            <h2>Dashboard del administrador</h2>
            <p class="muted">Gestiona usuarios y controla el estado de todos los pedidos.</p>
          </div>
        </div>

        <div class="stats">
          <div class="card stat"><div class="label">Usuarios</div><div class="value">{{ total_users }}</div></div>
          <div class="card stat"><div class="label">Pedidos</div><div class="value">{{ total_orders }}</div></div>
          <div class="card stat"><div class="label">Pendientes</div><div class="value">{{ pending }}</div></div>
          <div class="card stat"><div class="label">Completados</div><div class="value">{{ completed }}</div></div>
        </div>

        <div class="card panel" style="margin-bottom:22px;">
          <h2 style="font-size:1.3rem;">Pedidos</h2>
          <div class="card table-card" style="box-shadow:none; border:none; background:none;">
            {% if orders %}
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Usuario</th>
                  <th>Número</th>
                  <th>Mensaje</th>
                  <th>Estado</th>
                  <th>Fecha</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {% for order in orders %}
                <tr>
                  <td data-label="ID">#{{ order['id'] }}</td>
                  <td data-label="Usuario">{{ order['user_name'] }}<br><small>{{ order['user_email'] }}</small></td>
                  <td data-label="Número">{{ order['phone_number'] }}</td>
                  <td data-label="Mensaje">{{ order['message'] or 'Sin mensaje' }}</td>
                  <td data-label="Estado">
                    <span class="status status-{{ order['status'].lower()|replace('á','a')|replace('é','e')|replace('í','i')|replace('ó','o')|replace('ú','u') }}">{{ order['status'] }}</span>
                  </td>
                  <td data-label="Fecha">{{ order['created_at'] }}</td>
                  <td data-label="Acción">
                    <form method="post" action="{{ url_for('update_order_status', order_id=order['id']) }}">
                      <select name="status">
                        <option value="Pendiente" {% if order['status'] == 'Pendiente' %}selected{% endif %}>Pendiente</option>
                        <option value="Procesando" {% if order['status'] == 'Procesando' %}selected{% endif %}>Procesando</option>
                        <option value="Completado" {% if order['status'] == 'Completado' %}selected{% endif %}>Completado</option>
                        <option value="Cancelado" {% if order['status'] == 'Cancelado' %}selected{% endif %}>Cancelado</option>
                      </select>
                      <button class="btn btn-secondary" style="margin-top:8px; width:100%;" type="submit">Actualizar</button>
                    </form>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
            {% else %}
              <div class="empty">No hay pedidos todavía.</div>
            {% endif %}
          </div>
        </div>

        <div class="card panel">
          <h2 style="font-size:1.3rem;">Usuarios registrados</h2>
          <div class="card table-card" style="box-shadow:none; border:none; background:none;">
            {% if users %}
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Correo</th>
                  <th>Tipo</th>
                  <th>Fecha de registro</th>
                </tr>
              </thead>
              <tbody>
                {% for item in users %}
                <tr>
                  <td data-label="ID">#{{ item['id'] }}</td>
                  <td data-label="Nombre">{{ item['name'] }}</td>
                  <td data-label="Correo">{{ item['email'] }}</td>
                  <td data-label="Tipo">{{ 'Admin' if item['is_admin'] else 'Cliente' }}</td>
                  <td data-label="Fecha">{{ item['created_at'] }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
            {% else %}
              <div class="empty">No hay usuarios registrados.</div>
            {% endif %}
          </div>
        </div>
      </div>
    </div>
    """
    return render_page(
        content,
        title="Dashboard admin",
        user=user,
        orders=orders,
        users=users,
        total_orders=total_orders,
        total_users=total_users,
        pending=pending,
        completed=completed,
    )


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form.get("status", "Pendiente").strip()
    valid_statuses = {"Pendiente", "Procesando", "Completado", "Cancelado"}

    if status not in valid_statuses:
        flash("Estado inválido.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    flash("Estado del pedido actualizado.", "success")
    return redirect(url_for("admin_dashboard"))


@app.errorhandler(403)
def forbidden(_error):
    content = """
    <div class="page-wrap">
      <div class="container" style="max-width:720px;">
        <div class="card panel">
          <h2>Acceso denegado</h2>
          <p class="muted">No tienes permisos para entrar a esta página.</p>
          <a class="btn btn-primary" href="{{ url_for('home') }}">Volver al inicio</a>
        </div>
      </div>
    </div>
    """
    return render_page(content, title="Acceso denegado", user=current_user()), 403


if __name__ == "__main__":

    app.run(debug=True)

