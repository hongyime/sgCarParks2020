"""Nearest HDB car park lookup against the preserved, bundled CSV snapshot."""

import csv
import math
import re
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request, url_for

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "hdb-carpark-information.csv"
FIELDS = (
    "car_park_no", "address", "x_coord", "y_coord", "car_park_type",
    "type_of_parking_system", "short_term_parking", "free_parking",
    "night_parking", "car_park_decks", "gantry_height", "car_park_basement",
)
DECIMAL = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
COORDINATE_ERROR = "Enter both X and Y as finite numbers in SVY21 metres."


class CatalogUnavailable(ValueError):
    """The saved car park catalog cannot answer a query."""


def coordinate(value: object) -> float:
    text = str(value).strip()
    if len(text) > 64 or not DECIMAL.fullmatch(text):
        raise ValueError(COORDINATE_ERROR)
    number = float(text)
    if not math.isfinite(number):
        raise ValueError(COORDINATE_ERROR)
    return number


def store(path: Optional[Path] = None) -> list[dict[str, str]]:
    """Read each CSV row once; never append to or modify a shared catalog."""
    with (Path(path) if path is not None else DATA_PATH).open(
        encoding="utf-8-sig", newline=""
    ) as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(FIELDS):
            raise CatalogUnavailable("The saved car park data has an invalid header.")
        rows = []
        for row in reader:
            if None in row or any(row[field] is None for field in FIELDS):
                raise CatalogUnavailable("The saved car park data has an incomplete row.")
            if not row["car_park_no"] or not row["address"]:
                raise CatalogUnavailable("The saved car park data has an unnamed entry.")
            coordinate(row["x_coord"])
            coordinate(row["y_coord"])
            rows.append(row)
    return rows


carparks = store()
carpark_data = carparks  # Keep the original learning-project interface.
total_number_of_surface = sum(row["car_park_type"] == "SURFACE CAR PARK" for row in carparks)
total_number_of_multi = sum(row["car_park_type"] == "MULTI-STOREY CAR PARK" for row in carparks)


def calculate(x1: float, y1: float, x0: float, y0: float) -> float:
    distance = math.hypot(x1 - x0, y1 - y0)
    if not math.isfinite(distance):
        raise ValueError("Coordinates are too large. Enter SVY21 coordinates in metres.")
    return distance


def input_coords(x: object, y: object) -> list[dict]:
    input_x, input_y = coordinate(x), coordinate(y)
    return [
        {**row, "distance": calculate(input_x, input_y, float(row["x_coord"]), float(row["y_coord"]))}
        for row in carparks
    ]


def sortByDistance(x: object, y: object) -> list[dict]:
    """Return a stable sorted copy for callers that need every distance."""
    return sorted(input_coords(x, y), key=lambda row: row["distance"])


def nearest_entry(x: object, y: object, catalog: Optional[list[dict]] = None) -> dict:
    input_x, input_y = coordinate(x), coordinate(y)
    rows = carparks if catalog is None else catalog
    nearest, best_distance = None, math.inf
    for row in rows:
        distance = calculate(input_x, input_y, float(row["x_coord"]), float(row["y_coord"]))
        if distance < best_distance:
            nearest, best_distance = row, distance
    if nearest is None:
        raise CatalogUnavailable("The saved car park data is unavailable. Please try again later.")
    return {**nearest, "distance": best_distance}


def nearestCarpark(x_coord: object, y_coord: object) -> tuple[str, str]:
    nearest = nearest_entry(x_coord, y_coord)
    return nearest["car_park_no"], nearest["address"]


app = Flask(__name__)


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.endpoint == "static" and response.status_code < 400:
        response.cache_control.public = True
        response.cache_control.max_age = 3600
        response.cache_control.no_cache = None
    else:
        response.headers["Cache-Control"] = "no-store"
    return response


def page_context(**values) -> dict:
    return {
        "static_mode": False, "form_action": url_for("search"),
        "home_url": url_for("root"), "style_url": url_for("static", filename="style.css"),
        "catalog_count": len(carparks), "xcoords": "", "ycoords": "",
        "result": None, "error": None, **values,
    }


@app.get("/")
def root():
    return render_template("index.html", **page_context())


@app.get("/search")
def search():
    values = {name: request.args.get(name, "") for name in ("xcoords", "ycoords")}
    try:
        if any(len(request.args.getlist(name)) != 1 for name in values):
            raise ValueError(COORDINATE_ERROR)
        result = nearest_entry(values["xcoords"], values["ycoords"])
        return render_template("search.html", **page_context(**values, result=result))
    except CatalogUnavailable as error:
        return render_template("search.html", **page_context(**values, error=str(error))), 503
    except ValueError as error:
        return render_template("search.html", **page_context(**values, error=str(error))), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False, use_reloader=False)
