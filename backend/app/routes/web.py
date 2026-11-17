"""Dashboard HTML and administrator sessions."""

from flask import Blueprint, redirect, render_template, request, session

from ..auth import password_matches


blueprint = Blueprint("web", __name__)


@blueprint.get("/login")
def login_page():
    return render_template("login.html")


@blueprint.post("/login")
def login():
    if password_matches(request.form.get("password", "")):
        session.clear()
        session["admin"] = True
        return redirect("/")
    return render_template("login.html", error="Sai mật khẩu"), 401


@blueprint.post("/logout")
def logout():
    session.clear()
    return redirect("/login")


@blueprint.get("/")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")
    return render_template("index.html")
