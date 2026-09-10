"""Synthetic regression tests; no external services or database writes."""

import copy
import csv
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import main


def fixture(number, address, x, y):
    row = dict.fromkeys(main.FIELDS, '')
    row.update(car_park_no=number, address=address, x_coord=str(x), y_coord=str(y), car_park_type='SURFACE CAR PARK')
    return row


ROWS = [fixture('A', 'First, Road', 0, 0), fixture('B', 'Second Road', 10, 0), fixture('C', 'Third Road', 0, 10)]


class CatalogTests(unittest.TestCase):
    def test_quoted_csv_bom_and_embedded_newline(self):
        rows = [fixture('A', 'Block 1, Road\nUnit "Two"', 1, 2)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.csv'
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=main.FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            self.assertEqual(main.store(path), rows)
            self.assertEqual(main.store(path), rows)

    def test_file_relative_and_idempotent(self):
        before = copy.deepcopy(main.carparks)
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.assertEqual(main.store(), before)
                self.assertEqual(main.store(), before)
            finally:
                os.chdir(original)
        self.assertEqual(main.carparks, before)

    def test_malformed_csv_fails_instead_of_silently_losing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.csv'
            for content in ['wrong,header\na,b\n', ','.join(main.FIELDS) + '\nA,Incomplete\n']:
                with self.subTest(content=content):
                    path.write_text(content, encoding='utf-8')
                    with self.assertRaises(main.CatalogUnavailable):
                        main.store(path)

    def test_invalid_source_coordinates_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.csv'
            with path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=main.FIELDS)
                writer.writeheader()
                writer.writerow(fixture('A', 'Test Road', 'NaN', 1))
            with self.assertRaises(ValueError):
                main.store(path)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.rows = copy.deepcopy(ROWS)
        self.patch = patch.object(main, 'carparks', self.rows)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_distance_and_nearest(self):
        self.assertEqual(main.calculate(3, 4, 0, 0), 5)
        self.assertEqual(main.nearestCarpark(9, 0), ('B', 'Second Road'))

    def test_ties_preserve_csv_order(self):
        self.assertEqual(main.nearestCarpark(5, 0), ('A', 'First, Road'))

    def test_search_and_returned_rows_do_not_mutate_shared_catalog(self):
        sorted_rows = main.sortByDistance(9, 0)
        self.assertEqual([row['car_park_no'] for row in sorted_rows], ['B', 'A', 'C'])
        sorted_rows[0]['address'] = 'Changed copy'
        main.nearest_entry(0, 9)['address'] = 'Another changed copy'
        self.assertEqual(self.rows, ROWS)

    def test_nearest_does_not_sort_or_allocate_all_distances(self):
        with patch.object(main, 'sortByDistance', side_effect=AssertionError('sorting')), patch.object(main, 'input_coords', side_effect=AssertionError('full list')):
            self.assertEqual(main.nearestCarpark(9, 0)[0], 'B')

    def test_concurrent_queries_are_independent(self):
        coordinates = [(9, 0), (0, 9), (0, 0)] * 50
        with ThreadPoolExecutor(max_workers=8) as executor:
            found = list(executor.map(lambda xy: main.nearestCarpark(*xy)[0], coordinates))
        self.assertEqual(found, ['B', 'C', 'A'] * 50)
        self.assertEqual(self.rows, ROWS)

    def test_invalid_coordinates(self):
        for value in ['', ' ', None, True, 'NaN', 'Infinity', '-inf', '1e999', '0x10', '1_000', '1,000', '1x', '9' * 65, '１２']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                main.coordinate(value)

    def test_valid_decimal_coordinates(self):
        for value, expected in [(' 2.5 ', 2.5), ('.5', .5), ('1.', 1), ('+2e3', 2000), ('-1', -1), (0, 0)]:
            self.assertEqual(main.coordinate(value), expected)

    def test_overflow_is_validation_error(self):
        with self.assertRaisesRegex(ValueError, 'too large'):
            main.nearest_entry('1.79e308', '1.79e308')

    def test_empty_catalog(self):
        with self.assertRaises(main.CatalogUnavailable):
            main.nearest_entry(0, 0, [])


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.patch = patch.object(main, 'carparks', copy.deepcopy(ROWS))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.client = main.app.test_client()

    def test_home_and_result_work_without_javascript(self):
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        self.assertIn(b'action="/search"', home.data)
        result = self.client.get('/search?xcoords=9&ycoords=0')
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Second Road', result.data)
        self.assertIn(b'1 m', result.data)
        self.assertNotIn(b'<script', result.data)

    def test_invalid_missing_duplicate_and_nonfinite_queries_return_400(self):
        for query in ['', '?xcoords=1', '?xcoords=a&ycoords=2', '?xcoords=NaN&ycoords=1', '?xcoords=Infinity&ycoords=1', '?xcoords=1&xcoords=2&ycoords=1', '?xcoords=1.79e308&ycoords=1.79e308']:
            with self.subTest(query=query):
                response = self.client.get('/search' + query)
                self.assertEqual(response.status_code, 400)
                self.assertIn(b'role="alert"', response.data)

    def test_empty_catalog_returns_503(self):
        with patch.object(main, 'carparks', []):
            self.assertEqual(self.client.get('/search?xcoords=1&ycoords=1').status_code, 503)

    def test_template_escapes_source_and_query_values(self):
        main.carparks[0]['address'] = '<script>alert(1)</script>'
        result = self.client.get('/search?xcoords=0&ycoords=0')
        self.assertIn(b'&lt;script&gt;', result.data)
        self.assertNotIn(b'<script>', result.data)
        invalid = self.client.get('/search', query_string={'xcoords': '"><script>alert(1)</script>', 'ycoords': '0'})
        self.assertEqual(invalid.status_code, 400)
        self.assertNotIn(b'<script>', invalid.data)

    def test_cache_and_privacy_headers(self):
        html = self.client.get('/')
        self.assertEqual(html.headers['Cache-Control'], 'no-store')
        self.assertEqual(html.headers['Referrer-Policy'], 'no-referrer')
        self.assertEqual(html.headers['X-Content-Type-Options'], 'nosniff')
        asset = self.client.get('/static/style.css')
        self.assertEqual(asset.status_code, 200)
        self.assertIn('max-age=3600', asset.headers['Cache-Control'])
        asset.close()


if __name__ == '__main__':
    unittest.main()
