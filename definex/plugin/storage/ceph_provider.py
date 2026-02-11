from typing import List

import boto3
import polars as pl
from definex.plugin.storage.base import BaseStorageProvider

class CephProvider(BaseStorageProvider):
    def __init__(self, endpoint, ak, sk, bucket):
        self.s3 = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=ak, aws_secret_access_key=sk)
        self.bucket = bucket

    def save_batch(self, df: pl.DataFrame, trace_id: str) -> str:
        import io
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        key = f"spills/{trace_id}.parquet"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.getvalue())
        return f"dfx://ceph/{key}"

    def merge_parts(self, uris: List[str], target_id: str) -> str:
        # 使用 Ceph S3 的 Multi-part Copy 合并
        pass