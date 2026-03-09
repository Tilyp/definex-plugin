# 契约设计 (Code-as-Contract)

## 设计原则

1. **单一事实来源** - Python 类型注解是唯一的元数据来源
2. **自动生成** - 源码自动提取，无需手动维护
3. **智能合并** - 保留手动修改的 metadata
4. **深度约束** - 嵌套层级 ≤ 3 层，禁止黑盒类型

## manifest.yaml 结构

```yaml
plugin_info:
  id: "abc1234567890123"     # 16位全局唯一ID
  name: "my_plugin"          # 插件名称
  author: "Author"           # 作者
  version: "1.0.0"           # SemVer 版本
  description: "..."         # 描述
  icon: "⚡"                  # Emoji 图标

actions:
  - name: "greet"            # Action 名称
    category: "exec"          # 分类
    description: "..."       # 描述 (来自 docstring)
    location:                # 代码位置
      file: "main.py"       # 相对于 tools/ 的路径
      class: "MyPlugin"     # 类名
    inputSchema:            # 输入 Schema
      type: "object"
      properties:
        name:
          type: "string"
          description: "用户姓名"
          required: true
      required: ["name"]
    outputSchema:           # 输出 Schema
      type: "string"
      description: "欢迎语"
```

## 类型映射

| Python 类型 | Schema Type | 说明 |
|-------------|-------------|------|
| `str` | `string` | 字符串 |
| `int` / `float` | `number` | 数字 |
| `bool` | `boolean` | 布尔 |
| `list[T]` | `array` | 数组 (需泛型) |
| `bytes` | `blob` | 二进制 |
| 自定义 Class | `object` | 对象 |
| `dict` / `Any` | **INVALID** | 禁止使用 |

## Annotated 规范

```python
# ✅ 正确
def method(
    name: Annotated[str, "用户姓名"],
    age: Annotated[int, "年龄", 18]  # 带默认值
) -> Annotated[str, "返回值描述"]:
    ...

# ❌ 错误
def method(name: str, ...):           # 缺少描述
def method(name: Annotated[str], ...): # 缺少描述
def method(data: dict, ...):          # 禁止 dict
def method(data: Any, ...):           # 禁止 Any
```

## 嵌套深度限制

```python
# ✅ 正确 (3层)
class User:
    name: Annotated[str, "姓名"]
    profile: Annotated[UserProfile, "用户画像"]

class UserProfile:
    age: Annotated[int, "年龄"]
    email: Annotated[str, "邮箱"]

# ❌ 错误 (4层)
class User:
    profile: Annotated[Profile, "..."]
    
class Profile:
    detail: Annotated[Detail, "..."]  # 第4层，禁止
```

## 合约校验规则

### 1. 源码对齐
- manifest 中的 action 数量 = 源码中 @action 数量
- 方法签名完全一致

### 2. 强类型审计
- 禁止 `dict`、`Any`、`SimpleNamespace`
- 禁止裸 `list` (必须 `list[T]`)

### 3. 描述要求
- 所有参数必须有描述 (`Annotated[T, "描述"]`)
- 返回值必须有描述

### 4. 依赖规范
- `requirements.txt` 每行必须有版本约束
- 推荐格式: `package==1.0.0`

### 5. 安全扫描
- 禁止 `os.system`
- 禁止 `subprocess.call` (无 shell=True)
- 禁止 `eval`、`exec`
