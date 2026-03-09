# 配置与安全设计

## 配置管理

### 配置存储

```
~/.definex/
├── config.yaml      # 主配置文件 (加密)
├── .key            # AES 加密密钥
└── .cache/         # 缓存目录
    └── scanner/    # 扫描缓存
```

### 配置结构

```yaml
# config.yaml

push:
  default: "prod"
  
  environments:
    dev:
      url: "http://127.0.0.1:8000/upload"
      token: "dev-secret"
      timeout: 30
      enabled: true
      
    prod:
      url: "https://api.definex.com/upload"
      token: "prod-secret"
      timeout: 60
      enabled: true
```

### 配置加密

```python
# config/encryption.py

class ConfigEncryption:
    def __init__(self, key_file):
        self.key = self._load_or_generate_key(key_file)
    
    def encrypt(self, data: str) -> str:
        # AES-GCM 加密
        ...
    
    def decrypt(self, encrypted: str) -> str:
        # AES-GCM 解密
        ...
```

### 配置命令

```bash
# 配置发布环境
dfx plugin config push dev --url http://localhost:8000/upload --token dev-token
dfx plugin config push prod --url https://api.definex.com/upload --token prod-token

# 查看配置状态
dfx plugin config push

# 使用默认环境发布
dfx plugin push

# 指定环境发布
dfx plugin push -e prod
```

## 安全设计

### 1. 源码安全扫描

```python
# validator.py

DANGEROUS_CALLS = [
    "os.system",
    "subprocess.call",
    "eval(",
    "exec(",
]

def _check_security(self, root):
    for py_file in (root / "tools").rglob("*.py"):
        content = py_file.read_text()
        for call in DANGEROUS_CALLS:
            if call in content:
                self.console.print(f"⚠️ 警告: 包含危险调用: {call}")
```

### 2. 强类型约束

```python
# 禁止的类型
FORBIDDEN_TYPES = [
    "dict",
    "Dict",
    "Any",
    "SimpleNamespace",
]

# Scanner 检测
def _check_blackbox(self, action):
    for param, schema in action.get("inputSchema", {}).get("properties", {}).items():
        if schema.get("type") == "INVALID":
            raise ValidationError(f"禁止使用 {schema.get('error')}")
```

### 3. 嵌套深度限制

```python
MAX_NESTING_DEPTH = 3

def resolve_type(py_type, depth=0):
    if depth > MAX_NESTING_DEPTH:
        return {"type": "INVALID", "error": f"嵌套超过{depth}层"}
```

### 4. 配置安全

- Token 使用 AES-GCM 加密存储
- 敏感字段显示时脱敏 (`********`)
- 支持配置导入/导出 (可选择是否包含密钥)

### 5. 运行时隔离

```python
# sys.path 隔离
# libs/ 目录独立，不污染全局环境
# 临时目录解压，运行后自动清理
```

## 审计规则

| 检查项 | 规则 | 严重程度 |
|-------|------|---------|
| 危险调用 | os.system, eval, exec | 🔴 警告 |
| 黑盒类型 | dict, Any | 🔴 错误 |
| 缺少描述 | Annotated 无描述 | 🟡 警告 |
| 嵌套过深 | > 3 层 | 🔴 错误 |
| 依赖无版本 | requirements.txt 无版本 | 🔴 错误 |
| 源码不一致 | manifest 与代码不匹配 | 🔴 错误 |
