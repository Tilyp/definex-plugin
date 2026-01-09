import copy
from jsonschema import validate, ValidationError


class ParamsValidate:

    def validate(self, params: dict, schema: dict):
        """
        根据契约校验输入参数
        :param params: 用户传入的参数字典
        :param schema: Action 的 inputSchema
        """
        try:
            # 1. 预处理：针对 DefineX 特有的 'blob' 类型做兼容
            # JSON Schema 不原生支持 'blob'，我们在校验前将其视为 string 或 bytes 路径
            processed_schema = self._preprocess_schema(schema)
            # 2. 执行校验
            # jsonschema 自动处理必填(required)、类型(type)、枚举(enum)、默认值(default)
            validate(instance=params, schema=processed_schema)
        except ValidationError as e:
            # 3. 错误格式化：提取具体是哪个字段出了问题
            # e.path 是一个 collection，代表出错字段的层级路径
            field_path = ".".join([str(p) for p in e.path]) if e.path else "root"
            error_msg = f"契约校验失败: 字段 '[bold cyan]{field_path}[/bold cyan]' {e.message}"
            # self.console.print(Panel(
            #     error_msg,
            #     title="[bold red]Input Validation Error[/bold red]",
            #     border_style="red",
            #     expand=False
            # ))
            # 抛出自定义异常或直接终止
            raise ValueError(error_msg)

    def _preprocess_schema(self, schema: dict) -> dict:
        """
        递归转换 DefineX 特有标记为标准 JSON Schema
        """
        new_schema = copy.deepcopy(schema)

        def walk(node):
            if not isinstance(node, dict): return

            # 将 definex 的 blob 类型转换为标准 string (假设传输的是路径或Base64)
            if node.get("type") == "blob":
                node["type"] = "string"

            # 处理对象嵌套
            if "properties" in node:
                for v in node["properties"].values():
                    walk(v)

            # 处理数组嵌套
            if "items" in node:
                walk(node["items"])
            elif "item_schema" in node: # 兼容我们之前自定义的 item_schema 命名
                node["items"] = node.pop("item_schema")
                walk(node["items"])

        walk(new_schema)
        return new_schema