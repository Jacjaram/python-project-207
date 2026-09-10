from flask import Flask, render_template, request, redirect, url_for, flash
from page_analyzer.db import get_connection
import validators
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev"

# Límites para truncar campos
MAX_H1_LENGTH = 100
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 200


def truncate(text, max_length):
    """Trunca un texto y agrega '...' si excede el límite."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/urls")
def create_url():
    raw_url = request.form.get("url", "").strip()

    if not raw_url:
        flash("URL no válido", "danger")
        return render_template("index.html"), 422

    if len(raw_url) > 255:
        flash("URL no válido", "danger")
        return render_template("index.html"), 422

    if not validators.url(raw_url):
        flash("URL no válido", "danger")
        return render_template("index.html"), 422

    # Normalizar URL (extraer solo esquema + dominio)
    parsed = urlparse(raw_url)
    normalized = f"{parsed.scheme}://{parsed.netloc}"

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Verificar si ya existe (usando la URL normalizada)
        cur.execute("SELECT id FROM urls WHERE name = %s", (normalized,))
        existing = cur.fetchone()

        if existing:
            flash("La página ya existe", "danger")
            return redirect(url_for("show_url", id=existing[0]))

        # Guardar URL normalizada
        cur.execute(
            "INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id",
            (normalized, datetime.now())
        )
        url_id = cur.fetchone()[0]
        conn.commit()

        flash("La página se agregó correctamente", "success")
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
                c.status_code AS last_status_code
            FROM urls u
            LEFT JOIN (
                SELECT DISTINCT ON (url_id) url_id, status_code, created_at
                FROM url_checks
                ORDER BY url_id, created_at DESC
            ) c ON u.id = c.url_id
            ORDER BY u.id DESC
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
        url = cur.fetchone()

        if not url:
            flash("URL no encontrada", "danger")
            return redirect(url_for("list_urls"))

        url_name = url[0]

        # Hacer solicitud HTTP
        try:
            response = requests.get(url_name, timeout=10)
            response.raise_for_status()
            status_code = response.status_code

            soup = BeautifulSoup(response.text, "html.parser")

            h1_tag = soup.find("h1")
            h1 = h1_tag.get_text(strip=True) if h1_tag else ""

            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            meta = soup.find("meta", attrs={"name": "description"})
            description = meta.get("content", "").strip() if meta else ""

            # Truncar campos largos
            h1 = truncate(h1, MAX_H1_LENGTH)
            title = truncate(title, MAX_TITLE_LENGTH)
            description = truncate(description, MAX_DESCRIPTION_LENGTH)

            # Guardar verificación
            cur.execute("""
                INSERT INTO url_checks
                (url_id, status_code, h1, title, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id, status_code, h1, title, description, datetime.now()))
            conn.commit()

            flash("La página fue verificada correctamente", "success")

        except requests.RequestException:
            conn.rollback()
            flash("Error al verificar la página", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("show_url", id=id))