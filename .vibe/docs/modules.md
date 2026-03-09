# 模块设计

## CLI 模块

### cli.py
```
职责: 命令行入口
- 解析命令行参数
- 路由到 PluginManager
- 错误处理与提示
```

**命令架构:**
```
dfx plugin
├── init      # 初始化项目
├── manifest  # 契约同步
├── check     # 合规审计
├── watch     # 文件监听
├── build     # 隔离打包
├── push      # 云端发布
├── run       # 运行测试
│   ├── native  # 原生模式
│   └── mcp    # MCP 协议
├── config    # 配置管理
└── debug     # 远程调试
```

## Manager 模块

### PluginManager
```
职责: 业务编排中心
- 协调各组件工作
- 组件懒加载
- 工作流编排
```

**依赖组件:**
- Scanner (代码扫描)
- Validator (合规校验)
- ManifestGenerator (契约生成)
- ConfigManager (配置管理)
- Scaffolder (项目初始化)
- Builder (打包构建)
- Watcher (文件监控)
- Publisher (发布上传)
- Runner (运行执行)

## Core 模块

### Scanner (代码扫描)
```
职责: 提取 @action 装饰器
- AST 遍历
- 类型解析
- 缓存管理

关键类:
- CodeScanner
- OptimizedASTScanner
- CacheManager
```

### Translator (类型转换)
```
职责: Python → JSON Schema
- Annotated 解析
- 类型映射
- 嵌套深度控制

关键类:
- SchemaTranslator.resolve_type()
```

### Validator (合规校验)
```
职责: 代码与契约一致性
- 源码对齐检查
- Schema 深度校验
- 安全扫描
- 参数注解验证
```

### Watcher (文件监控)
```
职责: 开发监听
- watchdog 集成
- 事件批量处理
- 增量同步

关键类:
- PluginWatcher
- EventQueue
- OptimizedFileHandler
```

### Builder (打包构建)
```
职责: 依赖隔离打包
- uv/pip 安装
- libs 隔离
- 哈希缓存
- .dfxpkg 压缩
```

### Runner (运行执行)
```
职责: 插件执行
- Native 模式
- MCP 协议模式
- REPL 交互
```

## Runtime 模块

### PluginRuntime
```
职责: 运行时环境
- 解压 .dfxpkg
- sys.path 注入
- 动态模块加载
- 方法反射执行
- 流式响应处理
```

**执行流程:**
```
1. _prepare()
   └── 解压/加载 manifest.yaml

2. execute(action_meta, params, context)
   └── get_instance_by_action()
   └── method(**params)
   └── 检测 Generator → 自动采集
   └── 返回结果

3. execute_stream()
   └── 生成器模式
   └── StreamChunk[]
```

## SDK 模块

### BasePlugin
```python
class BasePlugin:
    def __init__(self, runtime_handle=None):
        self.runtime = runtime_handle
```

### @action 装饰器
```python
@action(category="exec", stream=False)
def my_method(self, 
    param: Annotated[str, "描述"]) -> Annotated[str, "返回值描述"]:
    ...
```

### ActionContext
```
职责: 执行上下文
- 生命周期管理
- 资源监控
- 事件发射
- 性能指标采集
```

### DataTypes
```python
STRING = "string"
NUMBER = "number"
BOOLEAN = "boolean"
ARRAY = "array"
OBJECT = "object"
BLOB = "blob"
NULL = "null"
```

## Storage 模块

### 存储抽象 (策略模式)
```
BaseStorageProvider (ABC)
├── MemoryProvider    # 共享内存
├── RustFSProvider   # RustFS
└── CephProvider     # Ceph
```

### 接口定义
```python
class BaseStorageProvider(ABC):
    def save_batch(df, trace_id) -> str: ...
    def merge_parts(uris, target_id) -> str: ...
    def get_physical_path(uri) -> str: ...
    def delete(uri): ...
```

## MCP 模块

### MCPAdapter
```
职责: Schema 转换
- DefineX → MCP Tool
- BLOB 类型处理
```

### DefineXMCPBridge
```
职责: MCP 服务桥接
- FastMCP 集成
- Action 注册
- 协议分发 (stdio/http/sse)
```
