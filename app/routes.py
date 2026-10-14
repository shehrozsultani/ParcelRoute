from flask import Blueprint, render_template, request

from .services import tracking

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("home.html", samples=tracking.sample_tracking_numbers())


@main.route("/track")
def track():
    raw = request.args.get("tn", "").strip()
    if not raw:
        return render_template("track.html", state="empty", tn="")
    if not tracking.is_valid_format(raw):
        return render_template("track.html", state="invalid", tn=raw)
    result = tracking.get_tracking(raw)
    if result is None:
        return render_template("track.html", state="notfound", tn=raw)
    return render_template("track.html", state="found", tn=raw, **result)


@main.route("/healthz")
def healthz():
    return {"status": "ok"}, 200
