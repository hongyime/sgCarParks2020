# Singapore Carparks

Find the nearest HDB car park from a pair of Singapore SVY21 coordinates.

[Open Singapore Carparks](https://hongyime.github.io/sgCarParks2020/)

## What the site does

Enter X (easting) and Y (northing) in metres. The result shows one car park number, address, type and estimated straight-line distance. Coordinates are not GPS latitude/longitude, and the result is not a driving route.

The site uses the original saved HDB CSV: 2,137 car parks. It does not show live availability, prices or closures. The CSV remains unchanged; `static/catalog.json` is a compact lookup derived from it, with one entry for every source record.

## Hosting and cost

The public application runs on the existing GitHub Pages site from the `master` branch root. Search runs in the browser. The catalog loads only after the first valid search and is reused for later searches on that page, with a 10-second download deadline and a 1 MiB response limit. There is no polling, external font/script request, Vercel function, Supabase query or new paid service.

The original Flask interface is also maintained and uses the same page template and dataset. The former Heroku demo returned HTTP 404 during the September 2026 maintenance check; a hosted Flask runtime has not been verified. GitHub Pages serves the static version, not Python.

## Run locally

Use Python 3.12 (the CI version):

```sh
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements.txt
python main.py
```

Open `http://127.0.0.1:5000`. Flask supports both `GET /` and `GET /search?xcoords=28000&ycoords=38000`, including browsers without JavaScript. Invalid or missing coordinates return a helpful HTTP 400 page.

For an existing Unix WSGI host, the `Procfile` uses one Gunicorn worker with two threads. Gunicorn is tested in Linux CI; it does not run natively on Windows. No server is provisioned by this repository.

## Build the Pages site

```sh
python scripts/build_pages.py
python scripts/build_pages.py --check
python -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000`. Commit the generated `index.html` and `static/catalog.json` when the template, CSS, JavaScript or CSV changes. The generator validates source rows, includes a source fingerprint, and versions asset URLs so updates do not silently reuse an older catalog. It never rewrites the source CSV.

## Verify changes

```sh
python -B -m unittest discover -s tests -p 'test_*.py' -v
npm test
python scripts/build_pages.py --check
```

Node.js 24 runs the browser-logic tests without installing npm packages. The Python tests cover quoted CSV data, file-relative/idempotent loading, input errors, stable ties, independent concurrent searches, safe HTML rendering and cache headers. Browser-logic tests cover matching geometry and validation, shared downloads, retries, size caps, and deadlines including stalled response bodies. Linux CI also starts the actual Gunicorn worker and checks both routes.

## Data and maintenance

Persistent data for this legacy application is the bundled public CSV. It has not been migrated into Supabase or deleted. Any future migration must preserve the original records and fit the portfolio's storage limits. This release restores the current app without adding cloud database traffic.

The visual style follows The Prawn Projects: monochrome, bold borders and offset shadows, with visible keyboard focus and a layout that works on small screens.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
