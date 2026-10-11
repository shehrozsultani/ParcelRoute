from datetime import datetime

from flask import Flask, render_template

from .config import Config
from . import db


def _as_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

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

    return app
