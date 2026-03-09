# DefineX - 工业级插件开发与编排脚手架

> 遵循 "Code-as-Contract" 设计哲学的插件系统底座

## 核心特性

- **代码即契约** - 利用 Python 类型系统作为元数据的单一事实来源
- **物理级环境隔离** - Vendor 模式 + .dfxpkg 打包
- **强契约低代码** - 禁止 dict/Any，强制类型建模
- **极速开发体验** - 热重载、增量缓存、智能扫描
- **协议同构** - 原生支持 MCP 协议

## 快速开始

```bash
# 安装
pip install uv
uv pip install -e .

# 初始化项目
dfx plugin init my_plugin

# 开发监听
dfx plugin watch

# 构建打包
dfx plugin build

# MCP 协议运行
dfx plugin run mcp --protocol stdio
```
