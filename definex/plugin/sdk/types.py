from typing import List


class ColumnInfo:
    name: str
    dtype: str
    description: str = ""

class TabularData:
    """大数据引用对象"""
    def __init__(self, uri: str, row_count: int, columns: List[ColumnInfo]):
        self.uri = uri
        self.row_count = row_count
        self.columns = columns
        self.is_ref = True

class Image:
    uri: str
    width: int
    height: int