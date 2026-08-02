"""
Web server for the ticker analyzer.

Run:
    pip install flask yfinance pandas numpy
    python app.py
Then open http://localhost:5000
"""
from flask import Flask, request, jsonify, send_from_directory
from analysis import analyze
from scan import run_scan
from movers import get_movers
from earnings import get_week_earnings

app = Flask(__name__, static_folder="static")


@app.route("/")
def home():
    return send_from_directory("static", "home.html")


@app.route("/scanner")
def index():
    return send_from_directory("static", "index.html")


@app.route("/scan")
def scan_page():
    return send_from_directory("static", "scan.html")


@app.route("/movers")
def movers_page():
    return send_from_directory("static", "movers.html")


@app.route("/earnings")
def earnings_page():
    return send_from_directory("static", "earnings.html")


@app.route("/about")
def about_page():
    return send_from_directory("static", "about.html")


@app.route("/methodology")
def methodology_page():
    return send_from_directory("static", "methodology.html")


@app.route("/api/analyze")
def api_analyze():
    ticker = request.args.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker provided"}), 400
    try:
        result = analyze(ticker)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan")
def api_scan():
    tickers_param = request.args.get("tickers")
    tickers = [t.strip().upper() for t in tickers_param.split(",")] if tickers_param else None
    try:
        results = run_scan(tickers)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/movers")
def api_movers():
    try:
        results = get_movers()
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/earnings")
def api_earnings():
    try:
        result = get_week_earnings()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG") == "1")
