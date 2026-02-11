import importlib.util
import inspect
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

from definex.plugin.sdk import StreamChunk, ActionContext


class PluginRuntime:
    def __init__(self, source_path: Path|str ):
        self.plugin_id = None
        self.source_path = Path(source_path).resolve()
        self.temp_dir = None
        self.plugin_root = None
        self.manifest = None
        self._prepare()
        self.actions = {}

    def _prepare(self):
        # 处理压缩包
        if self.source_path.is_file() and self.source_path.suffix == ".dfxpkg":
            self.temp_dir = tempfile.mkdtemp(prefix="dfx_rt_")
            with zipfile.ZipFile(self.source_path, 'r') as z: z.extractall(self.temp_dir)
            self.plugin_root = Path(self.temp_dir)
        else:
            self.plugin_root = self.source_path

        # 依赖与代码注入 (libs 优先)
        paths = [self.plugin_root / "libs", self.plugin_root / "tools"]
        for p in paths:
            if p.exists() and str(p) not in sys.path:
                sys.path.insert(0, str(p))

        with open(self.plugin_root / "manifest.yaml", "r", encoding="utf-8") as f:
            self.manifest = yaml.safe_load(f)
            self.actions = {a["name"]: a for a in self.manifest.get("actions", [])}
            self.plugin_id = self.manifest.get("plugin_id")

    def get_action_metadata(self, action_name: str) -> dict:
        """
        获取指定 Action 的元数据
        :param action_name: 方法名称
        :return: 包含 schema、location、is_streaming 等信息的字典
        """
        action_meta = self.actions.get(action_name)
        # 异常处理：如果找不到 Action
        if not action_meta:
            raise ValueError(f"❌ 契约错误: 在插件 '{self.plugin_id}' 中未找到名为 '{action_name}' 的 Action。")
        return action_meta

    def get_instance_by_action(self, action_meta: dict):
        action_name = action_meta["name"]
        mod_path = self.plugin_root / action_meta["location"]["file"]
        spec = importlib.util.spec_from_file_location("mod", str(mod_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        instance = getattr(module, action_meta["location"]["class"])
        return getattr(instance(), action_name)

    def execute(self, action_meta: dict, params: dict, context: ActionContext):
        method = self.get_instance_by_action(action_meta)
        # 1. 执行业务函数
        result =  method(**params)
        # 2. 自动识别 Generator（针对大数据/流式任务）
        if inspect.isgenerator(result):
            final_list = []
            for row in result:
                # 自动中断检查：用户无需写一行代码
                context.check_cancelled()

                # 自动数据采集与溢写监控
                context.collector.add(row)

                # 返回收集器的最终引用或数据
            return context.collector.get_result()
        # 3. 针对普通 return
        return result

    def execute_stream(self, action_meta: dict, params: dict, context: ActionContext):
        """执行流式 Action，返回一个 Python 生成器"""
        method = self.get_instance_by_action(action_meta)
        # 1. 执行方法获取结果
        result = method(**params)
        # 2. 判断是否为生成器
        if inspect.isgenerator(result):
            for chunk in result:
                if isinstance(chunk, StreamChunk):
                    yield chunk.to_dict()
                else:
                    # 兼容直接 yield 基础类型的情况
                    yield StreamChunk(delta=chunk).to_dict()
        else:
            # 如果不是生成器，将其包装成单次流返回（向下兼容）
            yield StreamChunk(delta=result, is_last=True).to_dict()

    def __del__(self):
        if self.temp_dir: shutil.rmtree(self.temp_dir)