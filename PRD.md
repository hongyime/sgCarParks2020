# PRD: sgCarParks2020

## Overview
A browser-based GitHub Pages application with a maintained Python Flask interface that helps Singapore residents find the nearest HDB car park to their current location using SVY21 coordinate input. Loads data from an official HDB car park CSV, computes Euclidean distance to each car park, and returns the nearest match. Built as a capstone/learning project.

## Goals
- Load and parse the official HDB car park information CSV
- Accept SVY21 (x, y) coordinates from the user
- Find the nearest car park using Euclidean distance
- Serve results on the existing GitHub Pages site and via the Flask web interface
- Return car park number and address

## Non-Goals
- Real-time availability data (does not use HDB real-time API)
- GPS/geolocation auto-detection
- Multiple nearby car parks (returns only the single nearest)
- Mobile app or native GPS integration
- Routing or directions

## User Stories
- As a driver, I want to find the nearest HDB car park by entering my current SVY21 coordinates.
- As a student, I want to build a location-based search using CSV data and Flask.

## Tech Stack
- **Language**: Python 3.x
- **Framework**: Flask
- **Libraries**: `math` (stdlib), `csv parsing` (stdlib)
- **Data**: `hdb-carpark-information.csv` (official HDB open data)

## Architecture
```
sgCarParks2020/
├── index.html                   # Generated public GitHub Pages application
├── scripts/build_pages.py       # Shared-template/CSV Pages generator
├── main.py                      # Flask app + server-side search logic
├── hdb-carpark-information.csv  # HDB open data (included in repo)
├── templates/
│   ├── index.html               # Home page with coordinate input form
│   └── search.html              # Results page
└── static/                      # CSS/JS assets
```

**Functions:**
- `store()` → parses CSV into list of dicts
- `calculate(x1, y1, x0, y0)` → Euclidean distance
- `input_coords(x, y)` → returns copies with a `distance` field; the shared catalog is unchanged
- `sortByDistance(x, y)` → stable O(n log n) sort of copied rows for compatibility
- `nearestCarpark(x, y)` → returns `(car_park_no, address)` from a single O(n) pass with stable source-order ties

**Routes:**
- `GET /` → `index.html`
- `GET /search?xcoords=&ycoords=` → finds nearest and renders `search.html`

## Features (detailed)

### CSV Parsing
- Reads `hdb-carpark-information.csv` once using file-relative `csv.DictReader`, including quoted commas, line breaks and UTF-8 BOMs; repeated loads do not append duplicates
- Extracts: `car_park_no`, `address`, `x_coord`, `y_coord`, `car_park_type`, `type_of_parking_system`, `short_term_parking`, `free_parking`, `night_parking`, `car_park_decks`, `gantry_height`, `car_park_basement`
- All values stored as strings (coordinates converted to float at calculation time)

### Distance Search
- Euclidean distance in SVY21 metre units
- One O(n) pass finds the nearest car park without sorting or modifying shared rows
- Missing, duplicate, invalid and nonfinite coordinate inputs produce a clear validation error
- Returns the car park number and address; the interface also shows type and rounded straight-line distance

### Security Headers
```python
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: no-referrer
Cache-Control: no-store  # HTML
Cache-Control: public, max-age=3600  # Successful Flask static assets
```

## Data / Config
| File | Description |
|------|-------------|
| `hdb-carpark-information.csv` | Source: data.gov.sg; 2000+ car parks with SVY21 coordinates |

## Deployment / Run
```bash
python -m pip install -r requirements.txt
python main.py
# open http://localhost:5000
# Enter SVY21 x,y coordinates (e.g. 28092, 29574 for Toa Payoh)
```

## Constraints & Notes
- **SVY21 coordinates**: Singapore's local projection system, not GPS lat/lng; typical range x: 2000–48000, y: 18000–50000
- **Euclidean ≠ geodesic**: uses straight-line distance, not walking/driving distance
- **Shared state**: query functions return copies and do not mutate the loaded catalog; concurrent query behavior is tested
- **Performance**: nearest lookup is O(n); browser searches reuse one compact catalog download per page session
- **Data freshness**: CSV is a static snapshot; HDB may have added/closed car parks since download

## Static production delivery

GitHub Pages publishes the master branch root. `scripts/build_pages.py` renders the shared template and derives a compact JSON catalog without modifying or dropping CSV records. Browser JavaScript validates input and finds one nearest match locally. The catalog is lazy-loaded once, with a 10-second deadline across headers and body, a 1 MiB size cap, and user-triggered retry after failure. There are no automatic refreshes, third-party runtime dependencies or cloud database calls. Static search needs JavaScript; Flask search works without it.

The public site is https://hongyime.github.io/sgCarParks2020/. The older Heroku endpoint returned 404 during maintenance. A separate hosted Flask runtime is unverified; test coverage alone does not establish that deployment.
