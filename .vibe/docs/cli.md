# CLI 命令参考

## 基础命令

### dfx plugin init
```bash
dfx plugin init <name>
```
初始化插件项目。

**交互参数:**
- 作者名称 (默认: DefineX)
- 版本号 (默认: 1.0.0)
- 图标选择
- 环境模式 (系统/虚拟环境)

**示例:**
```bash
dfx plugin init my_processor
```

---

### dfx plugin manifest
```bash
dfx plugin manifest [path] [--intent MODE]
```
扫描代码生成契约文件。

**参数:**
- `path`: 项目路径 (默认: .)
- `--intent`: 扫描模式
  - `default`: 默认
  - `strict`: 强制描述
  - `performance`: 侧重数据流

**示例:**
```bash
dfx plugin manifest .
dfx plugin manifest --intent strict
```

---

### dfx plugin check
```bash
dfx plugin check [path]
```
深度合规性检查。

**检查项:**
- 源码对齐
- Schema 校验
- 安全扫描
- 依赖规范

**示例:**
```bash
dfx plugin check
```

---

### dfx plugin watch
```bash
dfx plugin watch [path]
```
开发监听模式。

**功能:**
- 监听 tools/ 目录
- 自动 manifest + check
- 热重载

**示例:**
```bash
dfx plugin watch
```

---

### dfx plugin build
```bash
dfx plugin build [path]
```
构建隔离环境包。

**输出:**
- `*.dfxpkg` 文件

**示例:**
```bash
dfx plugin build
```

---

### dfx plugin push
```bash
dfx plugin push [path] [-e ENV] [--url URL] [--token TOKEN]
```
发布插件到服务器。

**参数:**
- `path`: 项目路径
- `-e, --env`: 目标环境 (dev/prod)
- `--url`: 手动指定 URL
- `--token`: 手动指定 Token

**示例:**
```bash
dfx plugin push
dfx plugin push -e prod
dfx plugin push --url https://api.example.com --token xxx
```

---

## 运行命令

### dfx plugin run native
```bash
dfx plugin run native [path] [options]
```
原生模式运行。

**选项:**
- `--action <name>`: 指定 Action
- `--params '<json>'`: JSON 参数
- `--repl`: 交互模式
- `--debug`: 调试模式
- `--watch`: 热重载

**示例:**
```bash
# 单次执行
dfx plugin run native --action greet --params '{"name": "World"}'

# 交互模式
dfx plugin run native --repl
```

---

### dfx plugin run mcp
```bash
dfx plugin run mcp [path] [options]
```
MCP 协议模式。

**选项:**
- `--protocol`: stdio/http/sse (默认: stdio)
- `--port`: 端口 (默认: 8080)
- `--watch`: 热重载

**示例:**
```bash
# Stdio 模式
dfx plugin run mcp --protocol stdio

# HTTP 模式
dfx plugin run mcp --protocol http --port 8080

# SSE 模式
dfx plugin run mcp --protocol sse --port 8080
```

---

## 配置命令

### dfx plugin config push
```bash
dfx plugin config push <env> [--url URL] [--token TOKEN]
```
配置发布环境。

**参数:**
- `env`: 环境名称 (dev/prod)
- `--url`: 服务器地址
- `--token`: 认证 Token

**示例:**
```bash
dfx plugin config push dev --url http://localhost:8000 --token dev-secret
dfx plugin config push prod --url https://api.example.com --token prod-secret
```

---

## 其他命令

### dfx plugin analyze
```bash
dfx plugin analyze [path] [--intent MODE]
```
代码质量分析。

### dfx plugin guide
```bash
dfx plugin guide [path]
```
交互式菜单。

### dfx plugin debug
```bash
dfx plugin debug [path] [-e ENV] [--protocol WS|SSE]
```
远程调试模式。
