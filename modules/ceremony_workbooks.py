"""Read-only, per-run cache of Excel's saved values and parsed tables."""

import os
import pandas as pd
from openpyxl import load_workbook


class CeremonyWorkbooks:
    def __init__(self):
        self.books = {}
        self.tables = {}

    def workbook(self, path):
        path = os.path.abspath(path)
        if path not in self.books:
            lock = os.path.join(os.path.dirname(path), '~$' + os.path.basename(path))
            if os.path.exists(lock):
                raise ValueError(f"Close Excel before running TOAST: {path}")
            self.books[path] = load_workbook(path, data_only=True)
        return self.books[path]

    def table(self, path, sheet, name):
        key = (os.path.abspath(path), sheet, name)
        if key not in self.tables:
            ws = self.workbook(path)[sheet]
            rows = list(ws[ws.tables[name].ref])
            headers = [str(c.value).strip() for c in rows[0]]
            if len(headers) != len(set(headers)):
                raise ValueError(f"Duplicate headers in {name}")
            values = [[c.value.strip() if isinstance(c.value, str) else c.value
                       for c in row] for row in rows[1:]]
            self.tables[key] = pd.DataFrame(values, columns=headers).replace('', None)
        return self.tables[key].copy()

    def close(self):
        for book in self.books.values():
            book.close()
        self.books.clear()
        self.tables.clear()
