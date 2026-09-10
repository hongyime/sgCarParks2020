"""Generate the GitHub Pages application from the same template and saved CSV."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import DATA_PATH, app, carparks  # noqa: E402


def assets() -> dict[str, bytes]:
    source_hash = hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()
    rows = [
        [row['car_park_no'], row['address'], float(row['x_coord']), float(row['y_coord']), row['car_park_type']]
        for row in carparks
    ]
    if not rows or len({row[0] for row in rows}) != len(rows):
        raise ValueError('The catalog must contain unique, nonempty car park entries.')
    catalog = (json.dumps({'schema': 1, 'source_sha256': source_hash, 'rows': rows}, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    if len(catalog) > 1024 * 1024:
        raise ValueError('The derived catalog exceeds the browser download limit.')

    def version(name: str) -> str:
        return hashlib.sha256((ROOT / 'static' / name).read_bytes()).hexdigest()[:16]

    with app.app_context():
        html = app.jinja_env.get_template('index.html').render(
            static_mode=True, form_action='./', home_url='./', catalog_count=len(rows),
            style_url=f'static/style.css?v={version("style.css")}',
            script_url=f'static/app.js?v={version("app.js")}',
            catalog_url=f'static/catalog.json?v={source_hash[:16]}', source_hash=source_hash,
            xcoords='', ycoords='', result=None, error=None,
        )
    return {'index.html': (html + '\n').encode('utf-8'), 'static/catalog.json': catalog}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if committed Pages files are stale.')
    args = parser.parse_args()
    for name, content in assets().items():
        target = ROOT / name
        if args.check:
            if not target.is_file() or target.read_bytes() != content:
                raise SystemExit(f'{name} is stale. Run python scripts/build_pages.py.')
        else:
            target.write_bytes(content)
        print(f'{"Checked" if args.check else "Generated"} {name}: {len(content)} bytes')


if __name__ == '__main__':
    main()
