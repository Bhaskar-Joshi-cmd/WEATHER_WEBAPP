from flask import Flask, render_template, request, redirect, url_for, flash
import requests, json, os

app = Flask(__name__)
app.secret_key = "weathernow_secret_key"

# Configure your API key (set env var OPENWEATHER_API_KEY or replace below)
API_KEY = os.getenv("OPENWEATHER_API_KEY") or '05608fca947a46639be08f910865d7ae'

FAV_FILE = "favorites.json"


# ---------- Helpers ----------
def load_favorite_names():
    """Return a list of city name strings (keeps your current file format)."""
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except json.JSONDecodeError:
            pass
    return []


def save_favorite_names(name_list):
    """Save a list of city name strings (keeps file simple)."""
    with open(FAV_FILE, "w") as f:
        json.dump(name_list, f, indent=2)


def fetch_weather(city):
    """Fetch live current weather from OpenWeatherMap.
    Returns a dict with keys (city, temperature, humidity, wind, pressure, condition)
    or {'city': city, 'error': '...'} on failure.
    """
    try:
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": API_KEY, "units": "metric"}
        r = requests.get(url, params=params, timeout=8)
        data = r.json()
    except Exception:
        return {"city": city, "error": "Network/API error"}

    # API returns cod != 200 on failure
    cod = data.get("cod")
    if cod != 200:
        return {"city": city, "error": data.get("message", "City not found")}

    try:
        return {
            "city": city,
            "temperature": round(float(data["main"].get("temp", 0)), 1),
            "humidity": int(data["main"].get("humidity", 0)),
            "wind": round(float(data.get("wind", {}).get("speed", 0)), 1),
            "pressure": int(data["main"].get("pressure", 0)),
            "condition": data.get("weather", [{}])[0].get("description", "").capitalize()
        }
    except Exception:
        return {"city": city, "error": "Malformed API response"}


# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    searched = None
    if request.method == "POST":
        searched = request.form.get("city", "").strip()
        if searched:
            result = fetch_weather(searched)
            if result and result.get("error"):
                flash(f"{result['city']}: {result['error']}", "danger")
    return render_template("index.html", result=result, searched=searched)


@app.route("/favorites")
def favorites():
    fav_names = load_favorite_names()
    fav_data = [fetch_weather(name) for name in fav_names]

    # Get sort and order parameters (normalize them)
    sort_by = request.args.get("sort_by", "city").strip().lower()
    order = request.args.get("order", "asc").strip().lower()
    reverse = (order == "desc")

    # Debug print to confirm incoming sort value
    print("Sorting by:", sort_by, "Order:", order)

    # --- Sorting logic ---
    def safe_key(item):
        if not item:
            return 0
        try:
            if "temp" in sort_by:  # catch 'temp', 'temperature', etc.
                return float(item.get("temperature", 0))
            elif "humid" in sort_by:
                return float(item.get("humidity", 0))
            elif "wind" in sort_by:
                return float(item.get("wind", 0))
            else:
                return item.get("city", "").lower()
        except Exception as e:
            print("Sort error:", e)
            return 0

    fav_data.sort(key=safe_key, reverse=reverse)

    return render_template("favorites.html", favorites=fav_data, sort_by=sort_by, order=order)


@app.route("/add_favorite/<city>")
def add_favorite(city):
    city = city.strip()
    if not city:
        return redirect(url_for("favorites"))
    favs = load_favorite_names()
    if not any(city.lower() == f.lower() for f in favs):
        favs.append(city)
        save_favorite_names(favs)
        flash(f"{city} added to favorites!", "success")
    else:
        flash(f"{city} is already in favorites.", "info")
    return redirect(url_for("favorites"))


@app.route("/remove_favorite/<city>")
def remove_favorite(city):
    favs = load_favorite_names()
    new = [f for f in favs if f.lower() != city.lower()]
    save_favorite_names(new)
    flash(f"{city} removed from favorites.", "info")
    return redirect(url_for("favorites"))


@app.route("/compare", methods=["GET"])
def compare():
    city1 = request.args.get("city1", "").strip()
    city2 = request.args.get("city2", "").strip()
    favs = load_favorite_names()

    data1 = fetch_weather(city1) if city1 else None
    data2 = fetch_weather(city2) if city2 else None

    return render_template("compare.html", favorites=favs, data1=data1, data2=data2, city1=city1, city2=city2)


if __name__ == "__main__":
    app.run(debug=True)
