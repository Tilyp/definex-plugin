# DefineX (dfx) - 插件开发与编排脚手架工具

---

## 第一章：设计思想 (Design Philosophy)

**DefineX** 是一个遵循 “契约先行 (Schema-First)” 设计哲学的插件系统底座。它通过强类型约束、深度元数据提取和物理级依赖隔离，确保插件在复杂工作流编排、AI Agent 调用（MCP 协议）及低代码平台中具备极高的**确定性**与**安全性**；DefineX架构遵循以下五大支柱：

1.  **代码即契约 (Code-as-Contract)**：
    利用 Python 的类型系统（Type Hints）作为元数据的单一事实来源。通过静态分析自动生成的 `inputSchema` 和 `outputSchema` 不仅用于前端 UI 渲染，也为 AI 代理（Agent）提供了精准的调用边界。
2.  **物理级环境隔离 (Physical Environment Isolation)**：
    拒绝依赖全局 Python 环境。通过 `libs/` 目录的 Vendor 模式，每个插件都携带自己特定版本的依赖。运行时动态修改 `sys.path` 优先级，确保插件逻辑在“纯净沙箱”中执行。
3.  **强契约低代码底座 (Strict Typing for Low-Code)**：
    DefineX 强制要求数据结构化。禁止使用 `dict` 和 `Any` 等黑盒对象，转而使用 POJO（纯 Python 类）建模。这种约束将不确定性扼杀在开发阶段，保障了编排流程中数据血缘（Data Lineage）的准确性。
4.  **极速开发体验**：内置热重载监听、交互式图标库、命名虚拟环境自动配置及增量缓存构建。 
5.  **协议同构 (Protocol Isomorphism)**：
    系统天然兼容 MCP 协议。DefineX 的 Action 定义与 MCP 的 Tool 定义在 Schema 层面 1:1 对齐，使得插件能够无缝切换于“工业级编排节点”与“AI 助手实时工具”两种身份。

---

## 第二章：源代码目录说明 (New Structure)

代码目前集中于 `definex/plugin` 模块，结构如下：

```text
definex/
└── plugin/                     # 插件系统核心包
    ├── core/                   # 逻辑处理引擎
    │   ├── builder.py          # 构建器：处理哈希增量同步与 .dfxpkg 打包
    │   ├── manifest_generator.py # 契约生成器：处理 manifest.yaml 的智能合并
    │   ├── runner.py           # 运行调度器：驱动 Native REPL 和 MCP 协议运行
    │   ├── scaffolder.py       # 脚手架：处理项目初始化、虚拟环境创建与模板注入
    │   ├── scanner.py          # 扫描器：负责递归扫描 tools/ 代码提取 Action
    │   ├── translator.py       # 翻译器：递归解析 Python 类型至标准 Schema
    │   ├── validator.py        # 校验器：执行源码对齐、黑盒拦截与安全审计
    │   ├── watcher.py          # 哨兵：实现开发模式下的热同步与实时校验
    │   └── utils.py            # 工具类：MD5 计算、目录静默清理等
    ├── templates/              # 预置模板 (发布包核心资源)
    │   ├── main.py.tmpl        # 逻辑入口模板
    │   ├── requirements.txt.tmpl # 依赖清单模板
    │   ├── spec.md.tmpl        # 开发手册模板
    │   └── simple/             # 分类建模样例 (config/list/nested/blob)
    ├── cli.py                  # 命令行入口：解析 dfx plugin ... 指令
    ├── sdk.py                  # 开发者 SDK：提供 BasePlugin、@action 与 DataTypes
    ├── runtime.py              # 运行时环境：处理解压、libs 加载与动态反射执行
    ├── mcp_adapter.py          # MCP 适配器：Schema 转换与数据清理
    ├── mcp_server.py           # MCP 服务端：集成 FastMCP 协议栈
    └── __init__.py             # 包声明
```

---

## 第三章：开发要求与准则

### 1. 结构与继承
- **业务代码归位**：所有逻辑代码必须位于插件根目录的 `tools/` 文件夹下。
- **类定义**：必须继承 `definex.plugin.sdk.BasePlugin`。
- **Action 标注**：对外暴露的方法必须添加 `@action(category="...")`。

### 2. 强类型模型 (禁止逃逸)
- **拒绝黑盒**：严禁在 `inputSchema` 和 `outputSchema` 路径中使用 `dict`、`Any`、`SimpleNamespace` 或裸写 `list`。
- **建模要求**：任何复合对象必须定义为一个 Python `class`。
- **描述要求**：所有参数和属性必须使用 `Annotated[Type, "Description"]`。描述将被作为前端 Label 和 LLM Prompt 使用。
- **深度限制**：嵌套层级（Object -> Object）严禁超过 **3 层**。

### 3. 构建与分发
- **版本控制**：插件版本号必须符合 **SemVer** (主版本.次版本.修订号) 规范。
- **依赖锁定**：`requirements.txt` 严禁不带版本号。必须指定如 `requests==2.31.0`。
- **环境预检**：在执行 `push` 之前，必须通过 `dfx plugin check` 的全量审计，确保“源码-契约” 100% 对齐。

### 4. 运行安全
- **敏感调用**：严禁在未声明的情况下调用 `os.system`、`eval`、`exec`。
- **IO 限制**：插件应尽量通过系统定义的 `blob` 类型处理文件，避免直接操作宿主机敏感目录。

---

## 第四章：常用开发指令 (核心路径)

1.  **开启新项目**：`dfx plugin init <name>`（建议选择虚拟环境模式）。
2.  **开发监听**：开启一个独立终端运行 `dfx plugin watch`，实时监控代码契约。
3.  **本地调试**：使用 `dfx plugin run native --repl` 进行函数逻辑验证。
4.  **AI 对接**：运行 `dfx plugin run mcp --protocol stdio` 并在 Cursor 中挂载。
5.  **发布构建**：执行 `dfx plugin build` 产生最终的 `.dfxpkg` 隔离环境包。


---


## 第五章：打包与安装 (DefineX CLI 本身)

如果您需要将 DefineX 部署到生产环境或分发给其他开发者，请遵循以下流程：

### 1. 编译打包
在 `setup.py` 所在的根目录下执行：
```bash
# 1. 安装构建工具
pip install build

# 2. 执行构建：生成源代码分发包 (tar.gz) 和二进制分发包 (wheel)
python -m build
```
构建产物将保存在 `dist/` 目录下：
- `definex-0.1.7-py3-none-any.whl` (推荐安装格式)
- `definex-0.1.7.tar.gz` (源码分发包)

### 2. 安装 DefineX CLI
**开发者模式 (推荐)**：
在开发环境下安装，修改代码后 `dfx` 命令实时生效。
```bash
cd DefineX
pip install -e .
```

**正式分发安装**：
```bash
pip install dist/definex-0.1.7-py3-none-any.whl
```

---

## 第六章： 插件开发快速开始

### 1. 指令架构树
```text
dfx
└── plugin
    ├── init        # 初始化项目
    ├── manifest    # 同步契约元数据
    ├── check       # 合规性与对齐审计
    ├── watch       # 自动化监听哨兵
    ├── build       # 隔离环境打包
    ├── push        # 发布至云端
    └── run         # 运行中心
        ├── native  # 原生执行 (Single/REPL/Debug)
        └── mcp     # 协议执行 (Stdio/HTTP/SSE)
```


### 2. 项目初始化 (init)
创建一个符合 DefineX 工业标准的插件工程。
- **命令**: `dfx plugin init <name>`
- **交互参数**:
    - **Author**: 插件作者。
    - **Version**: 初始版本号（默认 1.0.0）。
    - **Icon**: 从内置图标库选择一个代表插件功能的 Emoji。
    - **Environment**: 选择 `System` 或 `Virtual Env`（推荐，自动创建并配置隔离开发环境）。
- **产物**: 生成 `tools/`、`simple/` 样例、`spec.md` 及虚拟环境目录。

#### 2.1 编写 Action 逻辑
在 `tools/main.py` 中编写逻辑。必须继承 `BasePlugin` 并使用 `@action` 装饰器：
```python
from definex.plugin.sdk import BasePlugin, action
from typing import Annotated

class MyTool(BasePlugin):
    @action(category="exec")
    def greet(self, name: Annotated[str, "用户姓名"]) -> Annotated[str, "欢迎语"]:
        return f"Hello, {name}!"
```

### 3. 契约同步 (manifest)
扫描源码并更新 `manifest.yaml`，实现代码即契约。
- **命令**: `dfx plugin manifest [path]`
- **核心逻辑**:
    - 递归扫描 `tools/` 目录下所有被 `@action` 标注的方法。
    - 自动提取参数描述（Annotated）并生成 `inputSchema` 和 `outputSchema`。
    - **智能合并**: 保留手动修改的元数据，仅更新 actions 定义。

### 4. 合规性审计 (check)
在打包发布前执行“地狱级”严格检查，确保契约 100% 准确。
- **命令**: `dfx plugin check [path]`
- **校验项**:
    - **源码对齐**: 检查 Python 方法签名是否与 YAML 记录一致。
    - **契约审计**: 禁止 `dict`/`Any` 类型，强制要求字段描述，限制嵌套层级 ≤ 3。
    - **依赖检查**: 检查 `requirements.txt` 每一行是否都锁定了版本号。
    - **安全扫描**: 检索代码中是否包含 `eval`、`os.system` 等高危调用。

### 5. 自动化监听 (watch)
开启“哨兵模式”，实时监控开发变动。
- **命令**: `dfx plugin watch [path]`
- **触发逻辑**:
    - 监听 `tools/` 目录。
    - 文件保存时：**自动清屏** -> **自动 manifest** -> **自动 check**。
    - 开发者可以一边写代码，一边在终端实时查看合规反馈。

---

### 6. 运行中心 (run)

`run` 子命令支持两种截然不同的运行环境：

#### 6.1 原生测试模式 (native)
用于本地开发自测，不涉及网络协议。
- **命令**: `dfx plugin run native [path] [options]`
- **子模式**:
    - **单次执行**: `--action <name> --params '<json>'`（返回结果后退出）。
    - **REPL 交互**: `--repl`（启动交互式终端，支持连续发送指令）。
    - **程序交互 (Debug)**: `--debug`（启动标准 JSON 流接口，供外部程序作为子进程调用）。
- **可选开关**: `--watch`（代码变动后自动重载运行时缓存）。

#### 6.2 AI 协议模式 (mcp)
将插件转为标准 **Model Context Protocol** 服务，供 AI 客户端调用。
- **命令**: `dfx plugin run mcp [path] [options]`
- **协议选项**:
    - `--protocol stdio`: (默认) 标准输入输出，用于本地 Cursor/Claude 挂载。
    - `--protocol sse --port 8080`: SSE 持久连接，用于远程 AI 调用。
    - `--protocol http --port 8080`: 标准 HTTP 请求模式。
- **可选开关**: `--watch`（变动时自动刷新契约，保持 AI 识别的信息最新）。

### 7 打包与分发指令

#### 7.1 隔离构建 (build)
生成自包含的 `.dfxpkg` 插件包。
- **命令**: `dfx plugin build [path]`
- **核心动作**:
    - 强制执行 `check` 审计。
    - **依赖隔离**: 将 `requirements.txt` 依赖下载至包内 `libs/` 目录。
    - **增量同步**: 基于 Hash 判断，依赖未变动时秒级完成构建。
    - **排除冗余**: 自动剔除 `simple/` 样例、`__pycache__` 及虚拟环境目录。

#### 7.2 云端发布 (push)
- **命令**: `dfx plugin push [path] --url <url> --token <token>`
- **功能**: 执行 `build` 并在成功后将 `.dfxpkg` 上传至指定服务器，完成一键上线。

### 8 配置指令

#### 8.1 配置 llm (config)
- **命令**: dfx plugin config llm
  说明: 配置用于 AI 生成代码的大模型参数。
  参数:
  --api-key: 必填。你的 LLM 密钥。
  --model: 选填。默认 gpt-4o。
  --url: 选填。如果你使用代理（如中转接口）则需要填写。
  示例:
  ```shell
  dfx plugin config llm --api-key sk-xxx --model gpt-4o-mini
  ```

#### 8.2 配置 push (config)
- **命令**: dfx plugin config push
  说明: 配置默认的服务器发布信息，配置后执行 dfx plugin push 可不带参数。
  参数:
  --url: DefineX 接收包的 API 地址。
  --token: 个人访问令牌。
  示例: 
  ```shell
  dfx plugin config push --url https://api.dfx.com/v1/upload
  ``` 

- **命令**: 配置开发环境 
dfx plugin config push dev --url http://127.0.0.1:8000/upload --token dev-secret

- **命令**: 配置生产环境
dfx plugin config push prod --url https://api.definex.com/upload --token prod-secret-long-token

### 9. 发布指令

#### 9.1 发布到默认环境
  ```shell
  dfx plugin push
  ```

#### 9.2 切换环境发布
 通过 -e 快速切换目标：
- **命令**: 发布到生产环境
  ```shell
  dfx plugin push -e prod
  ```

- **命令**: 发布到开发环境
  ```shell
  dfx plugin push --env dev
  ```

### 10. AI 编程指令

- **命令**: dfx plugin code
  说明: 进入 AI 结对编程模式。
  工作流:
  系统自动读取当前 tools/ 目录下所有文件。
  将代码和 DefineX 开发规范发送给 LLM 作为上下文。
  开发者描述需求：“帮我加一个图片压缩 Action”。
  AI 生成符合 Annotated 规范的代码。
  输入 write：自动将代码写入 tools/main.py。
  选项: --chat 切换为纯咨询模式，不强制要求返回代码块。
---
**DefineX (dfx) - 让工具具备确定性，让编排具备生命力。**