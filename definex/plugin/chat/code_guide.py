"""
聊天命令处理器
"""
from typing import Dict, List, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.status import Status
from rich.table import Table

from definex.plugin.chat.commands import CommandHandler as BaseCommandHandler


class CodeGuide(BaseCommandHandler):
    """命令处理器"""

    def __init__(self, console: Console):
        super().__init__(console)
        self.console = console
        self._register_default_commands()

    def _register_default_commands(self):
        """注册默认命令"""
        self.register_command(
            name="help",
            description="显示帮助信息",
            handler=self._cmd_help,
            aliases=["h", "?"]
        )

        self.register_command(
            name="exit",
            description="退出对话",
            handler=self._cmd_exit,
            aliases=["quit", "q"]
        )

        self.register_command(
            name="clear",
            description="清空对话历史",
            handler=self._cmd_clear,
            aliases=["cls", "reset"]
        )

        self.register_command(
            name="write",
            description="保存最后生成的代码",
            handler=self._cmd_write,
            aliases=["save", "w"]
        )

        self.register_command(
            name="context",
            description="查看当前项目上下文",
            handler=self._cmd_context,
            aliases=["project", "proj"]
        )

        self.register_command(
            name="summary",
            description="查看对话摘要",
            handler=self._cmd_summary,
            aliases=["sum", "history"]
        )

        self.register_command(
            name="stats",
            description="查看对话统计",
            handler=self._cmd_stats,
            aliases=["statistics", "info"]
        )

        self.register_command(
            name="refresh",
            description="刷新项目上下文",
            handler=self._cmd_refresh,
            aliases=["reload", "update"]
        )

        self.register_command(
            name="manifest",
            description="创建或更新插件清单",
            handler=self._cmd_manifest,
            aliases=["init"]
        )

        self.register_command(
            name="models",
            description="查看可用AI模型",
            handler=self._cmd_models,
            aliases=["model", "llm"]
        )

        self.register_command(
            name="test",
            description="测试AI模型连接",
            handler=self._cmd_test,
            aliases=["ping", "connection"]
        )

        # 上下文管理命令
        self.register_command(
            name="save-context",
            description="保存当前对话上下文",
            handler=self._cmd_save_context,
            aliases=["save-ctx", "context-save"]
        )

        self.register_command(
            name="load-context",
            description="加载特定上下文",
            handler=self._cmd_load_context,
            aliases=["load-ctx", "context-load"]
        )

        self.register_command(
            name="list-contexts",
            description="列出所有保存的上下文",
            handler=self._cmd_list_contexts,
            aliases=["contexts", "ctx-list"]
        )

        self.register_command(
            name="clear-context",
            description="清除上下文 (使用 clear-context all 删除所有)",
            handler=self._cmd_clear_context,
            aliases=["delete-context", "ctx-clear"]
        )

        # 流程管理命令
        self.register_command(
            name="start-flow",
            description="启动代码生成流程",
            handler=self._cmd_start_flow,
            aliases=["flow-start", "begin-flow"]
        )

        self.register_command(
            name="next-stage",
            description="进入下一个流程阶段",
            handler=self._cmd_next_stage,
            aliases=["stage-next", "proceed"]
        )

        self.register_command(
            name="flow-status",
            description="查看流程状态",
            handler=self._cmd_flow_status,
            aliases=["status", "flow-info"]
        )

        self.register_command(
            name="reset-flow",
            description="重置代码生成流程",
            handler=self._cmd_reset_flow,
            aliases=["flow-reset", "restart-flow"]
        )

        self.register_command(
            name="write-test",
            description="保存测试代码到tests/目录",
            handler=self._cmd_write_test,
            aliases=["test-save", "save-test"]
        )

        self.register_command(
            name="cleanup-tests",
            description="清理测试文件",
            handler=self._cmd_cleanup_tests,
            aliases=["test-clean", "clean-tests"]
        )

        self.register_command(
            name="list-tests",
            description="列出所有测试文件",
            handler=self._cmd_list_tests,
            aliases=["tests", "test-list"]
        )


    # ===== 命令实现 =====

    def _cmd_help(self, args: List[str], context: Dict[str, Any]) -> Any:
        """帮助命令"""
        help_text = self.get_command_help()

        panel = Panel(
            help_text,
            title="可用命令",
            border_style="blue"
        )
        self.console.print(panel)

        return "help_shown"

    def _cmd_exit(self, args: List[str], context: Dict[str, Any]) -> Any:
        """退出命令"""
        confirm = Confirm.ask("[bold yellow]确认退出对话？[/bold yellow]", default=False)
        if confirm:
            return "exit"
        return None

    def _cmd_clear(self, args: List[str], context: Dict[str, Any]) -> Any:
        """清空历史命令"""
        conversation = context.get("conversation")
        if conversation:
            keep_system = len(args) > 0 and args[0] == "system"
            conversation.clear_history(keep_system=keep_system)

            if keep_system:
                self.console.print("[green]🔄 已清空对话历史（保留系统消息）[/green]")
            else:
                self.console.print("[green]🔄 已清空所有对话历史[/green]")

        return "history_cleared"

    def _cmd_write(self, args: List[str], context: Dict[str, Any]) -> Any:
        """保存代码命令"""
        writer = context.get("writer")
        root_path = context.get("root_path")
        conversation = context.get("conversation")
        if not writer or not root_path or not conversation:
            self.console.print("[red]❌ 无法保存代码：缺少必要的上下文[/red]")
            return None

        current_code = conversation.current_code
        if not current_code:
            self.console.print("[yellow]⚠️  没有可保存的代码[/yellow]")
            return None

        # 获取文件名
        filename = args[0] if args else "main.py"

        # 保存代码
        success, error = writer.write_code(
            root_path=root_path,
            code=current_code,
            filename=filename
        )

        if success:
            return "code_saved"
        else:
            self.console.print(f"[red]❌ 保存失败: {error}[/red]")
            return None

    def _cmd_context(self, args: List[str], context: Dict[str, Any]) -> Any:
        """查看上下文命令"""
        analyzer = context.get("analyzer")
        root_path = context.get("root_path")

        if not analyzer or not root_path:
            self.console.print("[red]❌ 无法显示上下文：缺少必要的上下文[/red]")
            return None

        analysis = analyzer.analyze_project(root_path, use_cache=True)
        analyzer.display_analysis(analysis, title="当前项目上下文")

        return "context_shown"

    def _cmd_summary(self, args: List[str], context: Dict[str, Any]) -> Any:
        """查看摘要命令"""
        conversation = context.get("conversation")

        if not conversation:
            self.console.print("[red]❌ 无法显示摘要：对话管理器未初始化[/red]")
            return None

        summary = conversation.get_conversation_summary()

        panel = Panel(
            summary,
            title="对话摘要",
            border_style="green"
        )
        self.console.print(panel)

        return "summary_shown"

    def _cmd_stats(self, args: List[str], context: Dict[str, Any]) -> Any:
        """查看统计命令"""
        conversation = context.get("conversation")

        if not conversation:
            self.console.print("[red]❌ 无法显示统计：对话管理器未初始化[/red]")
            return None

        stats = conversation.get_statistics()

        table = Table(title="对话统计", show_header=True, header_style="bold magenta")
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="green")

        table.add_row("总消息数", str(stats["total_messages"]))
        table.add_row("总Token数", str(stats["total_tokens"]))
        table.add_row("用户消息", str(stats["user_messages"]))
        table.add_row("助手消息", str(stats["assistant_messages"]))
        table.add_row("系统消息", str(stats["system_messages"]))
        table.add_row("平均Token/消息", f"{stats['average_tokens_per_message']:.1f}")

        self.console.print(table)

        return "stats_shown"

    def _cmd_refresh(self, args: List[str], context: Dict[str, Any]) -> Any:
        """刷新上下文命令"""
        analyzer = context.get("analyzer")
        conversation = context.get("conversation")
        root_path = context.get("root_path")

        if not analyzer or not conversation or not root_path:
            self.console.print("[red]❌ 无法刷新上下文：缺少必要的上下文[/red]")
            return None

        with Status("正在分析项目...", console=self.console):
            # 清除缓存
            analyzer.clear_cache()

            # 重新分析项目
            analysis = analyzer.analyze_project(root_path, use_cache=False)

            # 更新对话上下文
            conversation.set_project_context(analysis["summary"])

        self.console.print("[green]🔄 项目上下文已刷新[/green]")

        return "context_refreshed"

    def _cmd_manifest(self, args: List[str], context: Dict[str, Any]) -> Any:
        """创建清单命令"""
        writer = context.get("writer")
        root_path = context.get("root_path")

        if not writer or not root_path:
            self.console.print("[red]❌ 无法创建清单：缺少必要的上下文[/red]")
            return None

        with Status("正在创建清单文件...", console=self.console):
            success = writer.create_plugin_manifest(root_path)

        if success:
            self.console.print("[yellow]📋 请编辑 manifest.yaml 文件以配置插件信息[/yellow]")
            return "manifest_created"
        else:
            return None

    def _cmd_models(self, args: List[str], context: Dict[str, Any]) -> Any:
        """查看模型命令"""
        llm_client = context.get("llm_client")

        if not llm_client:
            self.console.print("[red]❌ 无法查看模型：LLM客户端未初始化[/red]")
            return None

        models = llm_client.get_available_models()

        if not models:
            self.console.print("[yellow]⚠️  没有可用的AI模型[/yellow]")
            return None

        table = Table(title="可用AI模型", show_header=True, header_style="bold cyan")
        table.add_column("模型名称", style="green")
        table.add_column("提供商", style="yellow")
        table.add_column("状态", style="cyan")
        table.add_column("描述", style="dim")

        for model in models:
            status = "✅ 当前" if model["is_current"] else "✓ 可用" if model["enabled"] else "✗ 禁用"
            table.add_row(
                model["name"],
                model["provider"],
                status,
                model["description"] or "暂无描述"
            )

        self.console.print(table)

        return "models_shown"

    def _cmd_test(self, args: List[str], context: Dict[str, Any]) -> Any:
        """测试连接命令"""
        llm_client = context.get("llm_client")

        if not llm_client:
            self.console.print("[red]❌ 无法测试连接：LLM客户端未初始化[/red]")
            return None

        model_name = args[0] if args else None

        with Status("正在测试连接...", console=self.console):
            result = llm_client.test_connection(model_name)

        if result["success"]:
            table = Table(title="连接测试结果", show_header=False, box=None)
            table.add_column("项目", style="cyan")
            table.add_column("数值", style="green")

            table.add_row("状态", "✅ 连接成功")
            table.add_row("模型", result["model"])
            table.add_row("提供商", result["provider"])
            table.add_row("延迟", result["latency"])
            table.add_row("响应", result["response"])

            if result["tokens_used"]:
                table.add_row("使用Token", str(result["tokens_used"]))

            self.console.print(table)
            return "test_passed"
        else:
            self.console.print(f"[red]❌ 连接失败: {result['error']}[/red]")
            return "test_failed"

    # ===== 上下文管理命令实现 =====

    def _cmd_save_context(self, args: List[str], context: Dict[str, Any]) -> Any:
        """保存上下文命令"""
        engine = context.get("engine")

        if not engine:
            self.console.print("[red]❌ 无法保存上下文：引擎未初始化[/red]")
            return None

        success = engine.save_current_context()
        if success:
            return "context_saved"
        else:
            return None

    def _cmd_load_context(self, args: List[str], context: Dict[str, Any]) -> Any:
        """加载上下文命令"""
        engine = context.get("engine")

        if not engine:
            self.console.print("[red]❌ 无法加载上下文：引擎未初始化[/red]")
            return None

        if not args:
            self.console.print("[yellow]⚠️  请提供上下文哈希值[/yellow]")
            self.console.print("[dim]使用 list-contexts 命令查看可用的上下文[/dim]")
            return None

        context_hash = args[0]
        success = engine.load_specific_context(context_hash)
        if success:
            return "context_loaded"
        else:
            return None

    def _cmd_list_contexts(self, args: List[str], context: Dict[str, Any]) -> Any:
        """列出上下文命令"""
        engine = context.get("engine")

        if not engine:
            self.console.print("[red]❌ 无法列出上下文：引擎未初始化[/red]")
            return None

        engine.list_all_contexts()
        return "contexts_listed"

    def _cmd_clear_context(self, args: List[str], context: Dict[str, Any]) -> Any:
        """清除上下文命令"""
        engine = context.get("engine")

        if not engine:
            self.console.print("[red]❌ 无法清除上下文：引擎未初始化[/red]")
            return None

        # 检查是否要删除所有上下文
        delete_all = False
        if args and args[0] in ["all", "--all", "-a"]:
            delete_all = True

        if delete_all:
            # 确认操作
            confirm = Confirm.ask("[bold red]⚠️  确认删除所有保存的上下文？[/bold red]", default=False)
            if not confirm:
                self.console.print("[yellow]操作已取消[/yellow]")
                return None

            success = engine.clear_current_context(delete_all=True)
            if success:
                return "all_contexts_cleared"
            else:
                return None
        else:
            # 只删除当前项目的上下文
            confirm = Confirm.ask("[bold yellow]确认清除当前项目的上下文？[/bold yellow]", default=False)
            if not confirm:
                self.console.print("[yellow]操作已取消[/yellow]")
                return None

            success = engine.clear_current_context(delete_all=False)
            if success:
                return "context_cleared"
            else:
                return None

    def _cmd_context_info(self, args: List[str], context: Dict[str, Any]) -> Any:
        """显示上下文信息命令"""
        conversation = context.get("conversation")
        engine = context.get("engine")

        if not conversation or not engine:
            self.console.print("[red]❌ 无法显示上下文信息：缺少必要的上下文[/red]")
            return None

        # 获取当前项目路径
        root_path = context.get("root_path")

        # 检查是否有保存的上下文
        has_saved_context = conversation.has_saved_context(root_path) if root_path else False

        # 获取对话统计
        stats = conversation.get_statistics()

        # 创建信息表格
        table = Table(title="上下文信息", show_header=False, box=None)
        table.add_column("项目", style="cyan", width=20)
        table.add_column("数值", style="green")

        table.add_row("项目路径", str(root_path) if root_path else "未设置")
        table.add_row("保存状态", "✅ 已保存" if has_saved_context else "❌ 未保存")
        table.add_row("消息总数", str(stats["total_messages"]))
        table.add_row("Token总数", str(stats["total_tokens"]))
        table.add_row("用户消息", str(stats["user_messages"]))
        table.add_row("助手消息", str(stats["assistant_messages"]))
        table.add_row("系统消息", str(stats["system_messages"]))
        table.add_row("平均Token/消息", f"{stats['average_tokens_per_message']:.1f}")

        # 如果有保存的上下文，显示更多信息
        if has_saved_context and root_path:
            try:
                context_dir = conversation.get_context_dir()
                filename = conversation.get_context_filename(root_path)
                file_path = context_dir / filename

                if file_path.exists():
                    import json
                    from datetime import datetime

                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    saved_at = data.get("metadata", {}).get("saved_at", "")
                    if saved_at:
                        try:
                            dt = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                            saved_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            pass

                    table.add_row("保存时间", saved_at)
                    table.add_row("文件位置", str(file_path))
                    table.add_row("上下文哈希", conversation.get_context_hash(root_path))

            except Exception as e:
                table.add_row("详细信息", f"获取失败: {e}")

        self.console.print(table)

        # 显示建议
        if not has_saved_context and stats["total_messages"] > 1:
            self.console.print("\n[dim]💡 提示: 使用 'save-context' 命令保存当前对话上下文[/dim]")

        return "context_info_shown"

    # ===== 流程管理命令实现 =====

    def _cmd_start_flow(self, args: List[str], context: Dict[str, Any]) -> Any:
        """启动流程命令"""
        from definex.plugin.chat.code_flow_manager import CodeFlowManager

        root_path = context.get("root_path")
        conversation = context.get("conversation")

        if not root_path:
            self.console.print("[red]❌ 无法启动流程：项目路径未设置[/red]")
            return None

        # 获取用户需求
        if not args:
            self.console.print("[yellow]⚠️  请提供需求描述[/yellow]")
            self.console.print("[dim]示例: start-flow 创建一个图片处理插件[/dim]")
            return None

        user_requirements = " ".join(args)

        # 初始化流程管理器
        flow_manager = CodeFlowManager(root_path)

        # 尝试加载现有流程
        if flow_manager.load_context():
            self.console.print("[yellow]⚠️  检测到现有流程，继续执行[/yellow]")
        else:
            # 启动新流程
            result = flow_manager.start_flow(user_requirements)
            if not result["success"]:
                self.console.print(f"[red]❌ 启动流程失败: {result['error']}[/red]")
                return None

        # 保存流程管理器到上下文
        context["flow_manager"] = flow_manager

        # 获取当前状态
        status = flow_manager.get_flow_status()

        # 显示流程信息
        table = Table(title="代码生成流程", show_header=False, box=None)
        table.add_column("项目", style="cyan", width=20)
        table.add_column("数值", style="green")

        table.add_row("项目名称", flow_manager.context.project_name)
        table.add_row("当前阶段", status["stage_name"])
        table.add_row("运行状态", "✅ 运行中" if status["is_running"] else "⏸️ 已暂停")
        table.add_row("进度", f"{status['progress']:.1f}%")
        table.add_row("创建时间", status["created_at"])
        table.add_row("更新时间", status["updated_at"])

        self.console.print(table)

        # 显示当前阶段说明
        current_stage = flow_manager.context.current_stage
        stage_instructions = {
            "requirement_analysis": "请详细描述您的需求，我会帮助您澄清和确认。",
            "intent_recognition": "让我分析您的真实意图，提供最适合的实现建议。",
            "architecture_design": "我将设计插件架构，包括类结构和方法设计。",
            "code_generation": "我将根据架构设计生成高质量的代码。",
            "test_generation": "我将为生成的代码编写测试用例。",
            "test_regression": "我将分析测试结果，提供修复建议。",
            "cleanup": "我将清理测试文件和临时文件。",
            "documentation": "我将生成完整的项目文档。"
        }

        instruction = stage_instructions.get(current_stage.value, "请继续描述您的需求。")
        self.console.print(f"\n[bold cyan]📋 当前阶段: {status['stage_name']}[/bold cyan]")
        self.console.print(f"[dim]{instruction}[/dim]")

        return "flow_started"

    def _cmd_next_stage(self, args: List[str], context: Dict[str, Any]) -> Any:
        """下一个阶段命令"""
        flow_manager = context.get("flow_manager")

        if not flow_manager:
            self.console.print("[red]❌ 无法进入下一阶段：流程未启动[/red]")
            self.console.print("[dim]请先使用 start-flow 命令启动流程[/dim]")
            return None

        # 进入下一个阶段
        result = flow_manager.proceed_to_next_stage()

        if not result["success"]:
            self.console.print(f"[red]❌ 进入下一阶段失败: {result['error']}[/red]")
            return None

        # 显示阶段信息
        self.console.print(f"[green]✅ 已进入 {result['stage_name']} 阶段[/green]")

        # 获取更新后的状态
        status = flow_manager.get_flow_status()

        table = Table(title="流程状态更新", show_header=False, box=None)
        table.add_column("项目", style="cyan", width=20)
        table.add_column("数值", style="green")

        table.add_row("当前阶段", status["stage_name"])
        table.add_row("进度", f"{status['progress']:.1f}%")
        table.add_row("已完成阶段", ", ".join(status["completed_stages"]))

        self.console.print(table)

        return "stage_changed"

    def _cmd_flow_status(self, args: List[str], context: Dict[str, Any]) -> Any:
        """流程状态命令"""
        flow_manager = context.get("flow_manager")

        if not flow_manager:
            self.console.print("[red]❌ 无法查看状态：流程未启动[/red]")
            self.console.print("[dim]请先使用 start-flow 命令启动流程[/dim]")
            return None

        # 获取流程状态
        status = flow_manager.get_flow_status()

        # 创建状态表格
        table = Table(title="代码生成流程状态", show_header=True, header_style="bold cyan")
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="green")

        table.add_row("项目名称", flow_manager.context.project_name)
        table.add_row("运行状态", "✅ 运行中" if status["is_running"] else "⏸️ 已暂停")
        table.add_row("当前阶段", status["stage_name"])
        table.add_row("进度", f"{status['progress']:.1f}%")
        table.add_row("创建时间", status["created_at"])
        table.add_row("更新时间", status["updated_at"])
        table.add_row("是否完成", "✅ 已完成" if status["completed"] else "⏳ 进行中")

        self.console.print(table)

        # 显示阶段详情
        if flow_manager.context.stage_data:
            self.console.print("\n[bold]📊 阶段详情:[/bold]")
            for stage, data in flow_manager.context.stage_data.items():
                stage_name = flow_manager._get_stage_name(stage)
                data_count = len(data)
                self.console.print(f"  • {stage_name}: {data_count} 条数据")

        # 显示建议
        if not status["completed"]:
            self.console.print("\n[dim]💡 提示: 使用 'next-stage' 命令进入下一阶段[/dim]")

        return "status_shown"

    def _cmd_reset_flow(self, args: List[str], context: Dict[str, Any]) -> Any:
        """重置流程命令"""
        flow_manager = context.get("flow_manager")

        if not flow_manager:
            self.console.print("[red]❌ 无法重置流程：流程未启动[/red]")
            return None

        # 确认操作
        confirm = Confirm.ask("[bold yellow]确认重置代码生成流程？[/bold yellow]", default=False)
        if not confirm:
            self.console.print("[yellow]操作已取消[/yellow]")
            return None

        # 重置流程
        result = flow_manager.reset_flow()

        if result["success"]:
            # 从上下文中移除流程管理器
            context.pop("flow_manager", None)
            self.console.print("[green]✅ 流程已重置[/green]")
            return "flow_reset"
        else:
            self.console.print(f"[red]❌ 重置失败: {result.get('error', '未知错误')}[/red]")
            return None

    def _cmd_current_stage(self, args: List[str], context: Dict[str, Any]) -> Any:
        """当前阶段命令"""
        flow_manager = context.get("flow_manager")

        if not flow_manager:
            self.console.print("[red]❌ 无法查看当前阶段：流程未启动[/red]")
            return None

        # 获取当前阶段信息
        current_stage = flow_manager.context.current_stage
        stage_name = flow_manager._get_stage_name(current_stage)

        # 获取提示词配置
        prompt_config = flow_manager.get_current_prompt_config()

        # 显示阶段信息
        panel = Panel(
            f"阶段: {stage_name}\n\n"
            f"状态: {prompt_config.state.value}\n"
            f"包含项目上下文: {'✅' if prompt_config.include_project_context else '❌'}\n"
            f"包含对话摘要: {'✅' if prompt_config.include_conversation_summary else '❌'}\n"
            f"包含代码示例: {'✅' if prompt_config.include_code_examples else '❌'}\n"
            f"最大上下文长度: {prompt_config.max_context_length}",
            title="当前阶段信息",
            border_style="blue"
        )
        self.console.print(panel)

        # 显示阶段说明
        stage_descriptions = {
            "requirement_analysis": "在此阶段，请详细描述您的需求。我会帮助您澄清模糊点，确认需求细节。",
            "intent_recognition": "在此阶段，我会分析您的真实意图，识别您想要创建什么类型的插件。",
            "architecture_design": "在此阶段，我会设计插件架构，包括类结构、方法设计和数据模型。",
            "code_generation": "在此阶段，我会根据架构设计生成高质量的代码。",
            "test_generation": "在此阶段，我会为生成的代码编写测试用例。",
            "test_regression": "在此阶段，我会分析测试结果，识别问题并提供修复建议。",
            "cleanup": "在此阶段，我会清理测试文件和临时文件。",
            "documentation": "在此阶段，我会生成完整的项目文档，包括README.md和API文档。"
        }

        description = stage_descriptions.get(current_stage.value, "请继续描述您的需求。")
        self.console.print(f"\n[bold]📝 阶段说明:[/bold]")
        self.console.print(f"[dim]{description}[/dim]")

        # 显示建议操作
        if current_stage.value == "requirement_analysis":
            self.console.print("\n[dim]💡 建议: 详细描述您的插件需求，包括功能、性能要求和约束条件[/dim]")
        elif current_stage.value == "code_generation":
            self.console.print("\n[dim]💡 建议: 确认架构设计后，我将开始生成代码[/dim]")

        return "current_stage_shown"

    # ===== 测试文件管理命令实现 =====

    def _cmd_write_test(self, args: List[str], context: Dict[str, Any]) -> Any:
        """保存测试文件命令"""
        writer = context.get("writer")
        root_path = context.get("root_path")
        conversation = context.get("conversation")

        if not writer or not root_path or not conversation:
            self.console.print("[red]❌ 无法保存测试文件：缺少必要的上下文[/red]")
            return None

        # 获取测试代码
        current_code = conversation.current_code
        if not current_code:
            self.console.print("[yellow]⚠️  没有可保存的测试代码[/yellow]")
            return None

        # 获取文件名
        test_filename = args[0] if args else "test_generated.py"

        # 保存测试文件
        success, error = writer.write_test_file(
            root_path=root_path,
            test_code=current_code,
            test_filename=test_filename
        )

        if success:
            return "test_file_saved"
        else:
            self.console.print(f"[red]❌ 保存测试文件失败: {error}[/red]")
            return None

    def _cmd_cleanup_tests(self, args: List[str], context: Dict[str, Any]) -> Any:
        """清理测试文件命令"""
        writer = context.get("writer")
        root_path = context.get("root_path")

        if not writer or not root_path:
            self.console.print("[red]❌ 无法清理测试文件：缺少必要的上下文[/red]")
            return None

        # 获取清理模式
        pattern = "test_*.py"
        confirm = True

        if args:
            if args[0] in ["all", "--all", "-a"]:
                pattern = "*.py"
            elif args[0] in ["force", "--force", "-f"]:
                confirm = False

        # 清理测试文件
        success, deleted_files = writer.cleanup_test_files(
            root_path=root_path,
            pattern=pattern,
            confirm=confirm
        )

        if success:
            if deleted_files:
                self.console.print(f"[green]✅ 已清理 {len(deleted_files)} 个测试文件[/green]")
            else:
                self.console.print("[yellow]⚠️  没有找到需要清理的测试文件[/yellow]")
            return "tests_cleaned"
        else:
            return None

    def _cmd_list_tests(self, args: List[str], context: Dict[str, Any]) -> Any:
        """列出测试文件命令"""
        writer = context.get("writer")
        root_path = context.get("root_path")

        if not writer or not root_path:
            self.console.print("[red]❌ 无法列出测试文件：缺少必要的上下文[/red]")
            return None

        # 获取测试文件列表
        test_files = writer.list_test_files(root_path)

        if not test_files:
            self.console.print("[yellow]⚠️  没有找到测试文件[/yellow]")
            return None

        # 显示测试文件列表
        table = Table(title="测试文件列表", show_header=True, header_style="bold cyan")
        table.add_column("文件名", style="green")
        table.add_column("路径", style="dim")
        table.add_column("大小", style="yellow")

        for test_file in test_files:
            try:
                size = test_file.stat().st_size
                size_str = f"{size:,} B"
                if size > 1024:
                    size_str = f"{size/1024:.1f} KB"
            except:
                size_str = "未知"

            table.add_row(
                test_file.name,
                str(test_file.relative_to(root_path)),
                size_str
            )

        self.console.print(table)

        # 显示统计信息
        self.console.print(f"\n[dim]总计: {len(test_files)} 个测试文件[/dim]")

        return "tests_listed"
