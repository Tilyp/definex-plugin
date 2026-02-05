import sys

import polars as pl

from .policy import ResourcePolicy


class RealtimeCollector:
    def __init__(self, context, storage):
        self._ctx = context
        self._storage = storage
        self._buffer = []
        self._size = 0
        self._uri = None

    def add(self, row: dict):
        self._buffer.append(row)
        self._size += sys.getsizeof(row)
        if self._size > ResourcePolicy.AUTO_SPILL_THRESHOLD_BYTES and not self._uri:
            self._spill()

    def _spill(self):
        df = pl.from_dicts(self._buffer)
        self._uri = self._storage.create_ref(df, prefer_shm=True)
        self._buffer = []
        self._ctx.report_progress(msg="Memory limit hit: switching to SHM mode.")

    def get_result(self):
        if self._uri: return {"uri": self._uri, "is_ref": True}
        return self._buffer

