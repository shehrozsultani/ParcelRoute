from datetime import datetime

from flask import Flask, render_template
import click

from .config import Config
from . import db
from .auth import auth
from .services import auth_service


def _as_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    _validate_secret_key(app)

    app.teardown_appcontext(db.close_db)

    @app.template_filter("dt")
    def fmt_dt(value):
        d = _as_dt(value)
        return d.strftime("%d %b %Y, %I:%M %p") if d else "—"

    @app.template_filter("fdate")
    def fmt_date(value):
        d = _as_dt(value)
        return d.strftime("%d %b %Y") if d else "—"

    @app.template_filter("money")
    def fmt_money(value):
        return "Rs. {:,.0f}".format(float(value)) if value is not None else "—"

    from .routes import main
    app.register_blueprint(main)
    app.register_blueprint(auth)

    @app.cli.command("init-auth-schema")
    def init_auth_schema_command():
        """Create the auth_users table if missing."""
        auth_service.init_auth_schema()
        click.echo("Auth schema initialized.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True, help="Admin username")
    @click.option("--role", default="admin", show_default=True,
                  type=click.Choice(sorted(auth_service.VALID_ROLES), case_sensitive=False))
    @click.password_option(confirmation_prompt=True)
    def create_admin_command(username, role, password):
        """Provision an admin/ops user without exposing plaintext passwords."""
        auth_service.init_auth_schema()
        auth_service.create_user(username, password, role)
        click.echo(f"User '{username}' created with role '{role}'.")

    @app.errorhandler(db.DatabaseError)
    def database_down(_err):
        return render_template("error.html",
                               title="Service temporarily unavailable",
                               message="We couldn't reach the logistics database. "
                                       "Please try again in a moment."), 503

    @app.errorhandler(404)
    def not_found(_err):
        return render_template("error.html", title="Page not found",
                               message="That page doesn't exist."), 404

    @app.errorhandler(400)
    def bad_request(_err):
        return render_template("error.html", title="Invalid request",
                               message="Your request could not be processed."), 400

    @app.errorhandler(403)
    def forbidden(_err):
        return render_template("error.html", title="Access denied",
                               message="You are not authorized to view this page."), 403

    return app


def _validate_secret_key(app):
    if app.config.get("TESTING"):
        return
    if app.config.get("APP_ENV", "production") != "production":
        return

    secret = app.config.get("SECRET_KEY", "")
    weak_defaults = {
        "",
        "dev-only-change-me",
        "change_me",
        "changeme",
        "secret",
        "default-secret",
    }
    if secret in weak_defaults or len(secret) < 32:
        raise RuntimeError(
            "SECRET_KEY is missing or weak for production. "
            "Set a strong random SECRET_KEY (32+ chars)."
        )
