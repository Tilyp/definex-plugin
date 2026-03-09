# 数据流设计

## 插件生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                      插件生命周期                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. init                                                        │
│  ┌──────────────┐                                               │
│  │ Scaffolder   │ → 创建项目结构 + 虚拟环境                      │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  2. develop (循环)                                              │
│  ┌──────────────┐                                               │
│  │   Scanner    │ → AST 扫描提取 @action                        │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │  Translator  │ → Python 类型 → JSON Schema                   │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │  Manifest    │ → 生成 manifest.yaml                           │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │  Validator   │ → 合规性审计                                   │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  3. watch (开发模式)                                            │
│  ┌──────────────┐                                               │
│  │   Watcher   │ → 文件监控 + 自动触发 manifest + check         │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  4. build                                                       │
│  ┌──────────────┐                                               │
│  │   Builder    │ → uv 安装依赖 → libs 隔离 → .dfxpkg 打包      │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  5. run                                                         │
│  ┌──────────────┐                                               │
│  │   Runner     │ → Native / MCP 模式执行                       │
│  └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  6. push                                                        │
│  ┌──────────────┐                                               │
│  │  Publisher   │ → 构建 + 上传服务器                            │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 代码 → 契约 数据流

```
tools/main.py
│
▼ @action 装饰器
┌─────────────────────────────────────────────┐
│ class MyPlugin(BasePlugin):                 │
│     @action(category="exec")                │
│     def greet(self,                          │
│         name: Annotated[str, "用户姓名"])    │
│         -> Annotated[str, "欢迎语"]:         │
│         return f"Hello, {name}!"            │
└─────────────────────────────────────────────┘
│
▼ Scanner (AST 遍历)
提取:
- class_name: "MyPlugin"
- method_name: "greet"
- category: "exec"
- params: ["name"]
- return_type: "Annotated[str, ...]"
│
▼ Translator (类型解析)
输入: Annotated[str, "用户姓名"]
输出:
{
  "type": "string",
  "description": "用户姓名",
  "required": true
}
│
▼ manifest.yaml
- name: "greet"
- category: "exec"
- description: "..."
- inputSchema: { type: "object", properties: {...} }
- outputSchema: { type: "string", description: "..." }
- location: { file: "main.py", class: "MyPlugin" }
```

## 运行时执行数据流

```
dfx plugin run native --action greet --params '{"name": "World"}'
│
▼ CLI 解析
args.action = "greet"
args.params = '{"name": "World"}'
│
▼ PluginRunner
1. 加载 PluginRuntime
   - 解压 .dfxpkg (如需要)
   - 注入 libs/ + tools/ 到 sys.path
   - 加载 manifest.yaml
│
2. 获取 Action 元数据
   action_meta = runtime.get_action_metadata("greet")
│
3. 动态加载模块
   module = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(module)
   instance = getattr(module, "MyPlugin")()
│
4. 执行方法
   result = instance.greet(name="World")
│
5. 返回结果
   "Hello, World!"
```

## MCP 协议数据流

```
AI Client (Cursor/Claude)
        │
        │ JSON-RPC
        ▼
┌───────────────────┐
│   FastMCP Server  │
│  (DefineXMCPBridge)│
└───────────────────┘
        │
        │ tools/call
        ▼
┌───────────────────┐
│  PluginRuntime    │
│  execute()        │
└───────────────────┘
        │
        │ result
        ▼
   JSON Response
```
