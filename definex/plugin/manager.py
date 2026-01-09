"""
DefineX 插件管理器 - 优化版本
职责：只做业务调用，不包含业务逻辑
"""

from pathlib import Path
from typing import Dict, Any, Optional, Annotated

from rich.console import Console

from definex.plugin.chat.engine import AICodeEngine
from definex.plugin.config.manager import ConfigManager
from definex.plugin.core.analyzer import CodeAnalyzer
from definex.plugin.core.builder import PluginBuilder
from definex.plugin.core.config_handler import create_config_handler, UnifiedConfigHandler
from definex.plugin.core.decorators import ensure_project
from definex.plugin.core.guide import InteractiveGuide
from definex.plugin.core.manifest_generator import ManifestGenerator
from definex.plugin.core.publisher import PluginPublisher
from definex.plugin.core.runner import PluginRunner
from definex.plugin.core.scaffolder import ProjectScaffolder
from definex.plugin.core.scanner import CodeScanner
from definex.plugin.core.validator import ProjectValidator
from definex.plugin.core.watcher import PluginWatcher
from definex.plugin.debugger.debug_orchestrator import DebugOrchestrator


class PluginManager:
    """插件管理器 - 只负责协调和调用业务组件"""

    def __init__(self):
        """按需初始化业务组件"""
        self.console = Console()

        # 核心依赖组件（被多个组件依赖，需要提前初始化）
        self.scanner = CodeScanner(self.console)
        self.validator = ProjectValidator(self.console, self.scanner)
        self.manifest_gen = ManifestGenerator(self.console, self.scanner)
        self.config_mgr = ConfigManager(self.console)

        # 延迟初始化的组件（按需创建）
        self._scaffolder = None
        self._builder = None
        self._watcher = None
        self._guide = None
        self._analyzer = None
        self._publisher = None
        self._ai_engine = None
        self._config_handler = None

    # ==================== 懒加载属性 ====================

    @property
    def scaffolder(self) -> ProjectScaffolder:
        """懒加载项目脚手架"""
        if self._scaffolder is None:
            self._scaffolder = ProjectScaffolder(self.console)
        return self._scaffolder

    @property
    def builder(self) -> PluginBuilder:
        """懒加载插件构建器"""
        if self._builder is None:
            self._builder = PluginBuilder(self.console, self.validator)
        return self._builder

    @property
    def watcher(self) -> PluginWatcher:
        """懒加载文件监控器"""
        if self._watcher is None:
            self._watcher = PluginWatcher(
                self.console, self.manifest_gen, self.validator, self.scanner
            )
        return self._watcher

    @property
    def guide(self) -> InteractiveGuide:
        """懒加载交互式引导"""
        if self._guide is None:
            self._guide = InteractiveGuide(self.console, self.config_mgr)
        return self._guide

    @property
    def analyzer(self) -> CodeAnalyzer:
        """懒加载代码分析器"""
        if self._analyzer is None:
            self._analyzer = CodeAnalyzer(self.console, self.scanner)
        return self._analyzer

    @property
    def config_handler(self) -> UnifiedConfigHandler:
        """懒加载统一配置处理器"""
        if self._config_handler is None:
            self._config_handler = create_config_handler(self.console, self.config_mgr)
        return self._config_handler

    # ==================== 核心业务调用方法 ====================

    @ensure_project
    def manifest(
        self,
        path: Annotated[str, "插件项目路径"],
        intent: Annotated[str, "扫描意图模式"] = "default"
    ) -> None:
        """
        生成契约文件 - 调用 ManifestGenerator

        Args:
            path: 插件项目路径
            intent: 扫描意图模式，可选值：default, strict, performance, security, cleanup
        """
        self.manifest_gen.generate(path, intent)

    @ensure_project
    def analyze(
        self,
        path: Annotated[str, "插件项目路径"],
        intent: Annotated[str, "分析意图模式"] = "strict"
    ) -> Dict[str, Any]:
        """
        分析代码质量 - 调用专门的 CodeAnalyzer

        Args:
            path: 插件项目路径
            intent: 分析意图模式，可选值：default, strict, performance, security, cleanup

        Returns:
            分析报告
        """
        return self.analyzer.analyze_code_quality(path, intent)

    @ensure_project
    def build(
        self,
        path: Annotated[str, "插件项目路径"]
    ) -> Optional[Path]:
        """
        构建插件 - 调用 PluginBuilder

        Args:
            path: 插件项目路径

        Returns:
            构建生成的包文件路径
        """
        return self.builder.run_build_flow(path)

    def init(
        self,
        name: Annotated[str, "项目文件夹名称"]
    ) -> None:
        """
        初始化项目 - 调用 ProjectScaffolder

        Args:
            name: 项目文件夹名称
        """
        self.scaffolder.run_init_flow(name)

    @ensure_project
    def guide_menu(
        self,
        path: Annotated[str, "插件项目路径"]
    ) -> None:
        """
        显示引导菜单 - 调用 InteractiveGuide

        Args:
            path: 插件项目路径
        """
        self.guide.menu_guide(Path(path))

    @ensure_project
    def check(
        self,
        path: Annotated[str, "插件项目路径"]
    ) -> bool:
        """
        检查项目 - 调用 ProjectValidator

        Args:
            path: 插件项目路径

        Returns:
            检查结果，True表示通过，False表示失败
        """
        return self.validator.validate_project(path)

    @ensure_project
    def watch(
        self,
        path: Annotated[str, "插件项目路径"]
    ) -> None:
        """
        监控文件变化 - 调用 PluginWatcher

        Args:
            path: 插件项目路径
        """
        self.watcher.start_watching(path)

    def config(
        self,
        section: Annotated[str, "配置节名称"],
        env: Annotated[str, "环境名称"] = None,
        api_key: Annotated[str, "API密钥"] = None,
        model: Annotated[str, "模型名称"] = None,
        base_url: Annotated[str, "基础URL"] = None,
        url: Annotated[str, "发布地址URL"] = None,
        token: Annotated[str, "认证令牌"] = None
    ) -> None:
        """
        管理配置 - 使用统一的配置处理器

        Args:
            section: 配置节名称 (llm/push/chat)
            env: 环境名称 (仅push配置使用)
            api_key: API密钥 (仅llm配置使用)
            model: 模型名称 (仅llm配置使用)
            base_url: 基础URL (仅llm配置使用)
            url: 发布地址URL (仅push配置使用)
            token: 认证令牌 (仅push配置使用)
        """
        if section == "llm":
            success = self.config_handler.configure_llm(
                model=model,
                api_key=api_key,
                base_url=base_url,
                provider=None,  # 使用默认值
                interactive=False
            )
            if success:
                self.config_handler.show_config_status("llm")
        elif section == "push":
            success = self.config_handler.configure_push(
                env=env,
                url=url,
                token=token,
                default=env,  # 如果指定了env，设为默认
                interactive=False
            )
            if success:
                self.config_handler.show_config_status("push")
        elif section == "chat":
            # Chat配置需要更多参数，这里简化处理
            data = {}
            if api_key:
                data["api_key"] = api_key
            if model:
                data["model"] = model
            if base_url:
                data["base_url"] = base_url

            success = self.config_handler.configure_chat(data, interactive=False)
            if success:
                self.config_handler.show_config_status("chat")
        else:
            self.console.print(f"[yellow]⚠️ 未知的配置节: {section}[/yellow]")
            self.console.print("[dim]支持的配置节: llm, push, chat[/dim]")

    @ensure_project
    def push(self, path: str, env: Optional[str] = None,
             url: Optional[str] = None, token: Optional[str] = None) -> None:
        """
        发布插件 - 调用 PluginPublisher

        Args:
            path: 插件路径
            env: 环境名称
            url: 发布URL
            token: 认证令牌
        """
        # 按需创建 Publisher
        if self._publisher is None:
            self._publisher = PluginPublisher(
                console=self.console,
                config_mgr=self.config_mgr,
                env_name=env,
                cmd_url=url,
                cmd_token=token
            )

        # 构建插件
        pkg_path = self.builder.run_build_flow(path)
        if not pkg_path:
            return

        # 发布插件
        self._publisher.publish(pkg_path)

    @ensure_project
    def code(
        self,
        path: Annotated[str, "项目路径"],
        mode: Annotated[str, "AI编程模式"] = "code"
    ) -> None:
        """
        AI编程辅助 - 调用 AICodeEngine

        Args:
            path: 项目路径
            mode: 模式 (code/chat等)
        """
        # 按需创建 AI 引擎
        if self._ai_engine is None:
            self._ai_engine = AICodeEngine(self.console, self.config_mgr)

        self._ai_engine.chat(path, mode=mode)

    def run(self, path: str, mode: str = "native", action: Optional[str] = None,
            params_json: Optional[str] = None, protocol: str = "stdio",
            port: int = 8080, watch: bool = False, repl: bool = False,
            debug: bool = False) -> Any:
        """
        运行插件 - 调用 PluginRunner

        Args:
            path: 插件路径
            mode: 运行模式 (native/mcp)
            action: 指定执行的action
            params_json: 参数JSON字符串
            protocol: 协议类型
            port: 端口号
            watch: 是否监控
            repl: 是否交互模式
            debug: 是否调试模式

        Returns:
            运行结果
        """
        runner = PluginRunner(self.console, path)
        return runner.run(
            mode=mode,
            action=action,
            params_json=params_json,
            protocol=protocol,
            port=port,
            watch=watch,
            repl=repl,
            debug=debug
        )

    @ensure_project
    def debug(self, path, env=None, protocol="ws"):
        """一键开启远程调试"""
        # 委托给编排器处理
        debug_orc = DebugOrchestrator(self.console, self.config_mgr, self.manifest_gen)
        return debug_orc.start(Path(path).resolve(), env_name=env, protocol=protocol)
