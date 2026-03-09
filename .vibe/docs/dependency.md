# 依赖隔离设计

## 设计目标

1. **物理级隔离** - 拒绝全局 Python 环境
2. **版本锁定** - 每个插件携带特定版本依赖
3. **增量构建** - 哈希缓存，秒级构建
4. **零冲突** - 插件间依赖互不影响

## 隔离方案

### Vendor 模式

```
my_plugin/
├── tools/           # 业务代码
│   └── main.py
├── libs/            # 隔离依赖 (vendor)
│   ├── requests/
│   ├── numpy/
│   └── ...
├── manifest.yaml    # 契约
├── requirements.txt
└── spec.md
```

### sys.path 注入

```python
# runtime.py

class PluginRuntime:
    def _prepare(self):
        # libs 优先于 tools
        paths = [
            self.plugin_root / "libs",
            self.plugin_root / "tools"
        ]
        
        for p in paths:
            if p.exists():
                sys.path.insert(0, str(p))
```

## 构建流程

```
dfx plugin build
│
▼ 1. 前置校验
│  validator.check_all()
│
▼ 2. 依赖同步
│  uv pip install -r requirements.txt --target libs/
│  (带哈希缓存，增量构建)
│
▼ 3. 沙箱组装
│  复制: tools/, libs/, manifest.yaml, requirements.txt
│  排除: simple/, __pycache__, .venv/
│
▼ 4. 清理冗余
│  删除 .pyc, __pycache__
│
▼ 5. 压缩打包
│  → my_plugin.dfxpkg (ZIP 格式)
```

## 哈希缓存

```python
# builder.py

def _sync_dependencies(root):
    req_file = root / "requirements.txt"
    libs_dir = root / "libs"
    hash_file = libs_dir / ".deps_hash"
    
    current_hash = get_file_hash(req_file)
    
    # 哈希匹配? 跳过安装
    if libs_dir.exists() and hash_file.exists():
        if hash_file.read_text() == current_hash:
            return True  # 使用缓存
    
    # 重新安装
    uv pip install -r requirements.txt --target libs/
    
    # 写入新哈希
    hash_file.write_text(current_hash)
```

## uv vs pip

```python
# 优先使用 uv
result = subprocess.run([
    "uv", "pip", "install",
    "-r", str(req_file),
    "--target", str(libs_dir),
    "--no-cache",
    "--system"
])

# uv 失败则回退 pip
if result.returncode != 0:
    return _sync_dependencies_fallback(...)
```

## 打包格式

```python
# .dfxpkg (ZIP)

my_plugin.dfxpkg
├── tools/
│   └── main.py
├── libs/
│   ├── requests/
│   └── ...
├── manifest.yaml
├── requirements.txt
└── .deps_hash
```

## 运行时加载

```python
# runtime.py

class PluginRuntime:
    def __init__(self, source_path):
        self.source_path = Path(source_path)
        
        # 解压 .dfxpkg
        if self.source_path.suffix == ".dfxpkg":
            self.temp_dir = tempfile.mkdtemp()
            zipfile.ZipFile(self.source_path).extractall(self.temp_dir)
            self.plugin_root = Path(self.temp_dir)
        else:
            self.plugin_root = self.source_path
        
        # 注入依赖路径
        for p in ["libs", "tools"]:
            path = self.plugin_root / p
            if path.exists():
                sys.path.insert(0, str(path))
        
        # 加载契约
        with open(self.plugin_root / "manifest.yaml") as f:
            self.manifest = yaml.safe_load(f)
```
