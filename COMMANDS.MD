# 🛠️ DefineX (dfx) 命令行操作全手册 (V1.0)

**DefineX CLI** 是插件开发者的核心工作台。它不仅处理底层的代码转换，更通过强有力的校验和自动化的监听流程，保证了插件生态的高质量。

---

## 1. 指令架构总览
```text
dfx
└── plugin
    ├── init        # 项目初始化
    ├── manifest    # 契约同步
    ├── check       # 合规审计
    ├── watch       # 自动化监听哨兵
    ├── build       # 隔离环境打包
    ├── push        # 云端发布
    ├── config      # 全局配置管理 (LLM/Push)
    ├── code        # AI 结对编程
    ├── debug       # 远程调试隧道
    └── run         # 运行测试中心
        ├── native  # 原生执行 (Single/REPL/Debug)
        └── mcp     # 协议执行 (Stdio/SSE/HTTP)
```

---

## 2. 插件生命周期管理

### 2.1 项目初始化 (init)
创建一个符合 DefineX 工业标准的插件工程。
*   **命令**: `dfx plugin init <name>`
*   **参数说明**: `<name>` 为项目文件夹名。
*   **执行逻辑**:
    1.  **交互式收集**: 引导输入作者、版本及描述。
    2.  **图标库**: 提供 Emoji 图标选择器。
    3.  **环境构建**: 询问是否创建虚拟环境。若选择 `Venv`，将自动创建 `{{name}}_env` 文件夹并执行 `pip install -r requirements.txt`。
*   **示例**:
    ```shell
    dfx plugin init my_processor
    ```

### 2.2 契约同步 (manifest)
扫描源码并更新 `manifest.yaml`，实现“代码即契约”。
*   **命令**: `dfx plugin manifest [path] [--intent MODE]`
*   **参数说明**:
    *   `path`: 项目路径，默认为当前目录 `.`。
    *   `--intent`: 扫描模式。`default`(默认), `strict`(强制描述), `performance`(侧重数据流)。
*   **执行逻辑**: 递归扫描 `tools/` 目录，提取 `Annotated` 描述和类型提示，转化为 `inputSchema` 和 `outputSchema`。支持**智能合并**，保留手动修改的非冲突字段。
*   **示例**:
    ```shell
    dfx plugin manifest . --intent strict
    ```

### 2.3 合规性审计 (check)
在打包发布前执行全量合规性扫描。
*   **命令**: `dfx plugin check [path]`
*   **校验核心**:
    *   **对齐检查**: 比对 Python 方法签名与 `manifest.yaml` 是否 100% 同步。
    *   **强类型审计**: 拦截 `dict`、`Any`、未指定泛型的 `list`。
    *   **递归深度**: 限制嵌套对象层级 ≤ 3 层。
    *   **安全扫描**: 检索 `os.system` 等高危调用。
*   **示例**:
    ```shell
    dfx plugin check
    ```

### 2.4 自动化监听 (watch)
开启“哨兵模式”，实时监控开发变动。
*   **命令**: `dfx plugin watch [path]`
*   **功能**: 持续监听 `tools/` 目录。每当文件保存，立即触发：**自动清屏 -> 自动 manifest -> 自动 check**。
*   **示例**:
    ```shell
    dfx plugin watch
    ```

---

## 3. 配置与发布指令

### 3.1 全局配置管理 (config)
管理敏感的 API Key 和服务器地址，信息采用 **AES 加密** 存储在 `~/.definex/config.yaml`。
*   **子命令 1: LLM 配置**
    ```shell
    # 配置 OpenAI 模型
    dfx plugin config llm openai --api-key sk-xxx --model gpt-4o
    ```
*   **子命令 2: Push 环境配置**
    ```shell
    # 配置生产环境地址
    dfx plugin config push prod --url https://api.dfx.com/upload --token sk-tok-123
    ```

### 3.2 隔离构建 (build)
生成全自包含的 `.dfxpkg` 插件包。
*   **命令**: `dfx plugin build [path]`
*   **逻辑**: 强制执行 `check` -> 同步依赖至包内 `libs/` -> 写入 `.deps_hash` (增量构建) -> 封装。
*   **示例**:
    ```shell
    dfx plugin build
    ```

### 3.3 云端发布 (push)
*   **命令**: `dfx plugin push [path] [-e ENV]`
*   **逻辑**: 自动触发 `build` 并将结果推送至指定环境（默认使用 config 中的 `default`）。
*   **示例**:
    ```shell
    dfx plugin push -e prod
    ```

---

## 4. 运行与调试中心 (run)

### 4.1 原生测试模式 (native)
不涉及网络协议，直接在本地执行逻辑。支持**智能参数识别**：若最后一个参数为 JSON 字符串，系统会自动识别为 `params_json`。
*   **单次模式**:
    ```shell
    dfx plugin run native --action calculate --params '{"x": 1}'
    # 或简写:
    dfx plugin run native --action calculate . '{"x": 1}'
    ```
*   **交互模式 (REPL)**:
    ```shell
    dfx plugin run native --repl
    # 进入后可输入: action_name {"key": "val"}
    ```
*   **程序模式 (Debug)**:
    ```shell
    dfx plugin run native --debug
    # 采用 JSON Line 协议，适合外层主程序调用
    ```

### 4.2 AI 协议模式 (mcp)
将插件转为标准 **Model Context Protocol** 服务。
*   **Stdio 模式** (本地挂载):
    ```shell
    dfx plugin run mcp --protocol stdio
    ```
*   **SSE 模式** (远程托管):
    ```shell
    dfx plugin run mcp --protocol sse --port 8080
    ```

---

## 5. 高级 AI 与调试指令

### 5.1 AI 辅助编码 (code)
*   **命令**: `dfx plugin code [path] [--chat]`
*   **工作流**: 系统提取当前 `tools/` 代码摘要发送给 LLM。开发者输入“增加一个图片去噪功能”，AI 生成代码。输入 `write` 即可回写文件。
*   **示例**:
    ```shell
    dfx plugin code
    ```

### 5.2 远程调试隧道 (debug)
将本地源码实时挂载到云端工作流。
*   **命令**: `dfx plugin debug [-e ENV] [--protocol {ws, sse}]`
*   **逻辑**: 通过 WebSocket 或 SSE 建立安全隧道。云端执行到该节点时，数据透传至本地运行并回传结果。
*   **示例**:
    ```shell
    dfx plugin debug -e dev --protocol ws
    ```

---

## 6. 类型映射规范速查表

| DefineX 标准类型 | Python 类型定义 | 约束项 |
| :--- | :--- | :--- |
| **`string`** | `str` | 必须带 `Annotated` 描述 |
| **`number`** | `int` / `float` | 必须带 `Annotated` 描述 |
| **`boolean`** | `bool` | 必须带 `Annotated` 描述 |
| **`array`** | `list[T]` | **强制泛型 T**，严禁裸写 `list` |
| **`blob`** | `bytes` | 映射为二进制文件流 |
| **`object`** | `自定义 Class` | 自动展开属性，严禁 > 3 层嵌套 |
| **`INVALID`** | `dict` / `Any` | **严禁使用** |
