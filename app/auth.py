import secrets
from functools import wraps

from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .services import auth_service

auth = Blueprint("auth", __name__)


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def permission_required(permission):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            role = session.get("role")
            if not auth_service.has_permission(role, permission):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


@auth.app_context_processor
def inject_auth_context():
    return {
        "csrf_token": get_csrf_token(),
        "current_user": {
            "user_id": session.get("user_id"),
            "username": session.get("username"),
            "role": session.get("role"),
        }
        if session.get("user_id")
        else None,
    }


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        get_csrf_token()
        return render_template("login.html", error=None)

    _require_csrf()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template("login.html", error="Invalid username or password."), 400

    user = auth_service.authenticate_user(username, password)
    if user is None:
        return render_template("login.html", error="Invalid username or password."), 401

    session.clear()
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True

    return redirect(url_for("main.home"))


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    _require_csrf()
    session.clear()
    return redirect(url_for("main.home"))


@auth.route("/admin")
@permission_required("admin:access")
def admin_page():
    return render_template("admin.html")


@auth.route("/ops")
@permission_required("ops:access")
def ops_page():
    return render_template("ops.html")


def _require_csrf():
    form_token = request.form.get("csrf_token", "")
    session_token = session.get("csrf_token", "")
    if not form_token or not session_token or form_token != session_token:
        abort(400)
