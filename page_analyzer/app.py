from flask import Flask, render_template, request, redirect, url_for, flash
from page_analyzer.db import get_connection
import validators
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = "dev"


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/urls")
def create_url():
    url = request.form.get("url", "").strip()

    if not url:
        flash("URL inválida", "danger")
        return redirect(url_for("index"))

    if len(url) > 255:
        flash("URL demasiado larga (máx 255 caracteres)", "danger")
        return redirect(url_for("index"))

    if not validators.url(url):
        flash("URL inválida", "danger")
        return redirect(url_for("index"))

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM urls WHERE name = %s", (url,))
        existing = cur.fetchone()

        if existing:
            flash("URL ya existe", "warning")
            return redirect(url_for("show_url", id=existing[0]))

        cur.execute(
            "INSERT INTO urls (name) VALUES (%s) RETURNING id",
            (url,)
        )

        url_id = cur.fetchone()[0]
        conn.commit()

        flash("URL añadida correctamente", "success")
        return redirect(url_for("show_url", id=url_id))

    finally:
        cur.close()
        conn.close()

@app.get("/urls")
def list_urls():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                u.id,
                u.name,
                u.created_at,
                MAX(c.created_at) AS last_check
            FROM urls u
            LEFT JOIN url_checks c ON u.id = c.url_id
            GROUP BY u.id, u.name, u.created_at
            ORDER BY u.created_at DESC
        """)

        urls = cur.fetchall()
        return render_template("urls.html", urls=urls)

    finally:
        cur.close()
        conn.close()


@app.get("/urls/<int:id>")
def show_url(id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, name, created_at FROM urls WHERE id = %s", (id,))
        url = cur.fetchone()

        if not url:
            return "URL no encontrada", 404

        cur.execute("""
            SELECT id, status_code, h1, title, description, created_at
            FROM url_checks
            WHERE url_id = %s
            ORDER BY id DESC
        """, (id,))

        checks = cur.fetchall()

        return render_template("url.html", url=url, checks=checks)

    finally:
        cur.close()
        conn.close()


@app.post("/urls/<int:id>/checks")
def create_check(id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT name FROM urls WHERE id = %s", (id,))
        url = cur.fetchone()[0]

        if not url.startswith("http"):
            url = "https://" + url
        headers = {
        "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        status_code = response.status_code

        soup = BeautifulSoup(response.text, "html.parser")

        h1_tag = soup.find("h1")
        h1 = h1_tag.get_text(strip=True) if h1_tag else ""

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        meta = soup.find("meta", attrs={"name": "description"})
        description = meta["content"] if meta else ""

        cur.execute("""
            INSERT INTO url_checks
            (url_id, status_code, h1, title, description, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (id, status_code, h1, title, description))

        conn.commit()

        flash("Página analizada correctamente", "success")

    except requests.RequestException:
        conn.rollback()
        flash("Ocurrió un error al hacer la verificación", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("show_url", id=id))