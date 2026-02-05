import os

class DataTypes:
    STRING, NUMBER, BOOLEAN = "string", "number", "boolean"
    ARRAY, OBJECT, BLOB, NULL = "array", "object", "blob", "null"
    IMAGE, VIDEO, AUDIO, DATAFRAME = "image", "video", "audio", "dataframe"

class ResourcePolicy:
    # 5MB 自动溢写阈值
    AUTO_SPILL_THRESHOLD_BYTES = int(os.getenv("DFX_MEMORY_THRESHOLD", 5 * 1024 * 1024))
    MAX_NESTING_DEPTH = 3
