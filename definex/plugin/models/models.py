from typing import Annotated


class FileObject:
    name: Annotated[str, "文件名"]
    path: Annotated[str, "完整路径或Key"]
    size: Annotated[int, "文件大小(Bytes)"]
    last_modified: Annotated[str, "最后修改时间"]

class StorageConfig:
    provider: Annotated[str, "存储供应商: local, s3, ftp"]
    endpoint: Annotated[str, "服务器地址"]
    access_key: Annotated[str, "访问Key或用户名"]
    secret_key: Annotated[str, "密钥或密码"]
    bucket: Annotated[str, "桶名或根目录"]