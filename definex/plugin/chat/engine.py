"""
AI代码引擎主模块
"""
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.status import Status

from definex.core import LLMClientManager
from definex.plugin.config import ConfigManager
from .analyzer import ProjectAnalyzer
from .code_guide import CodeGuide
from .conversation import ConversationManager, MessageRole
from .text_utils import TextCleaner
from .todo_generator import TODOGenerator
from .writer import CodeWriter


class AICodeEngine:
    """AI代码引擎主类"""

    def __init__(self, console: Console, config_mgr: ConfigManager):
        self.console = console

        # 初始化配置管理器
        self.config_mgr = config_mgr

        # 初始化组件
        self.conversation = ConversationManager()
        self.analyzer = ProjectAnalyzer(console)
        self.writer = CodeWriter(console)
        self.commands = CodeGuide(console)
        self.llm_client = LLMClientManager()
        self.text_cleaner = TextCleaner()
        self.todo_generator = TODOGenerator()

        # 状态变量
        self.project_root: Optional[Path] = None
        self.current_model: Optional[str] = None
        self.is_running = False
        self._flow_manager = None  # 代码流程管理器
        # 加载配置
        self._load_config()


    def _load_config(self):
        """加载配置"""
        try:
            # 加载LLM配置
            llm_config = self.config_mgr.get_llm_config()

            if not llm_config.models:
                self.console.print("[yellow]⚠️  未配置AI模型[/yellow]")
                return

            # 初始化模型
            for model_name, model_config in llm_config.models.items():
                if model_config.enabled:
                    try:
                        self.llm_client.add_model(model_config)
                        self.console.print(f"[green]✓ 加载模型: {model_name}[/green]")
                    except Exception as e:
                        self.console.print(f"[red]❌ 加载失败: {model_name} - {e}[/red]")

            # 设置当前模型
            if llm_config.current_model:
                self.llm_client.set_current_model(llm_config.current_model)
                self.console.print(f"[cyan]当前模型: {llm_config.current_model}[/cyan]")

        except Exception as e:
            self.console.print(f"[red]❌ 配置加载失败: {e}[/red]")

    def initialize_project(self, root_path: str) -> bool:
        """初始化项目"""
        try:
            self.project_root = Path(root_path).resolve()

            # 尝试加载保存的上下文
            self._try_load_context()

            # 分析项目
            with Status("正在分析项目...", console=self.console):
                analysis = self.analyzer.analyze_project(self.project_root)
                self.analyzer.display_analysis(analysis)

            # 设置项目上下文
            self.conversation.set_project_context(analysis["summary"])

            # 显示上下文状态
            self._display_context_status()

            return True
        except Exception as e:
            self.console.print(f"[red]❌ 初始化失败: {e}[/red]")
            return False

    def start_chat(self, mode: str = "code"):
        """开始聊天"""
        if not self.project_root:
            self.console.print("[red]❌ 请先初始化项目[/red]")
            return

        if not self.llm_client.get_current_client():
            self.console.print("[red]❌ 没有可用的AI模型[/red]")
            return

        self.is_running = True
        self._show_welcome(mode)

        while self.is_running:
            try:
                # 获取用户输入
                user_input = Prompt.ask(
                    "\n[bold cyan]💭 您的需求[/bold cyan]",
                    default="",
                    show_default=False
                ).strip()

                if not user_input:
                    continue
                # 检查命令
                if self.commands.is_command(user_input):
                    self._handle_command(user_input)
                    continue

                # 处理用户输入
                self._process_user_input(user_input)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]⏸️  已暂停[/yellow]")
            except Exception as e:
                self.console.print(f"[red]❌ 处理失败: {e}[/red]")
                self.conversation.record_error()

    def _handle_command(self, command_text: str):
        """处理命令"""
        context = {
            "conversation": self.conversation,
            "analyzer": self.analyzer,
            "writer": self.writer,
            "llm_client": self.llm_client,
            "root_path": self.project_root,
            "engine": self
        }
        result = self.commands.execute_command(command_text, context)

        if result == "exit":
            # 调用stop()方法，这会触发自动保存
            self.stop()

    def _process_user_input(self, user_input: str):
        """处理用户输入 - 添加步骤打印"""
        # 显示处理步骤开始
        self.console.print("\n[bold cyan]🔧 开始处理用户输入...[/bold cyan]")

        # 检查是否是需求描述（自动启动流程）
        if self._is_requirement_description(user_input):
            self.console.print("\n[bold cyan]🔍 检测到需求描述，自动启动代码生成流程...[/bold cyan]")

            # 自动生成TODO
            self._generate_todo_from_requirements(user_input)

            # 自动启动代码生成流程
            self._auto_start_code_flow(user_input)

            return

        # 步骤1: 添加到历史
        self.console.print("[dim]📝 步骤1: 添加用户消息到对话历史[/dim]")
        self.conversation.add_message(MessageRole.USER, user_input)

        # 步骤2: 获取API消息
        self.console.print("[dim]📝 步骤2: 准备API请求消息[/dim]")
        messages = self.conversation.get_messages_for_api(user_input)

        # 步骤3: 调用AI
        self.console.print("[dim]📝 步骤3: 调用AI模型生成响应[/dim]")
        response = self._call_ai(messages)

        if response:
            # 步骤4: 添加到历史
            self.console.print("[dim]📝 步骤4: 添加AI响应到对话历史[/dim]")
            self.conversation.add_message(MessageRole.ASSISTANT, response)

            # 步骤5: 提取代码块
            self.console.print("[dim]📝 步骤5: 提取响应中的代码块[/dim]")
            code_blocks = self.conversation.extract_code_blocks(response)

            if code_blocks:
                self.console.print(f"[dim]📝 检测到 {len(code_blocks)} 个代码块[/dim]")

                # 步骤6: 智能选择代码块
                self.console.print("[dim]📝 步骤6: 智能选择最佳代码块[/dim]")
                selected_code = self._select_best_code_block(code_blocks)
                self.conversation.current_code = selected_code

                # 显示代码块信息
                lines = selected_code.split('\n')
                char_count = len(selected_code)
                self.console.print(f"[dim]📝 选择的代码块: {len(lines)} 行, {char_count} 字符[/dim]")

                # 提示用户保存
                self.console.print(f"\n[bold green]✅ 代码生成完成！[/bold green]")
                self.console.print(f"[dim]📝 检测到代码块，使用 'write <文件名>' 命令保存[/dim]")
                self.console.print(f"[dim]💡 示例: write main.py 或 write plugin.py[/dim]")
            else:
                self.console.print("[dim]📝 响应中未检测到代码块[/dim]")
        else:
            self.console.print("[yellow]⚠️  AI响应为空，请检查网络连接或模型配置[/yellow]")

    def _select_best_code_block(self, code_blocks: List[str]) -> str:
        """智能选择最佳的代码块"""
        if len(code_blocks) == 1:
            return code_blocks[0]

        # 评分系统：给每个代码块打分
        scored_blocks = []
        for i, code in enumerate(code_blocks):
            score = 0

            # 检查是否包含类定义（+10分）
            if 'class ' in code and 'def ' in code:
                score += 10

            # 检查是否包含import语句（+5分）
            if 'import ' in code or 'from ' in code:
                score += 5

            # 检查是否包含BasePlugin（+15分）
            if 'BasePlugin' in code:
                score += 15

            # 检查代码长度（适中的长度更好）
            lines = len(code.split('\n'))
            if 10 <= lines <= 100:  # 适中的代码长度
                score += 5
            elif lines > 100:  # 太长的代码可能是完整的文件
                score += 10

            # 检查是否包含使用示例（减分）
            if 'plugin.execute' in code or 'print(' in code and 'def ' not in code:
                score -= 5

            scored_blocks.append((score, i, code))

        # 按分数排序，选择分数最高的
        scored_blocks.sort(reverse=True, key=lambda x: x[0])

        # 显示选择结果（调试信息）
        if len(scored_blocks) > 1:
            self.console.print(f"[dim]从 {len(code_blocks)} 个代码块中选择第 {scored_blocks[0][1]+1} 个（分数: {scored_blocks[0][0]}）[/dim]")

        return scored_blocks[0][2]

    def _call_ai(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """调用AI - 添加详细的步骤打印"""
        try:
            # 获取状态显示
            state = self.conversation.conversation_state
            state_text = {
                "initial": "🤖 初始对话",
                "chat": "💬 普通聊天",
                "code_gen": "👨‍💻 代码生成",
                "review": "🔍 代码审查",
                "debug": "🐛 调试",
                "refactor": "🔄 重构"
            }.get(state.value, "🤖 AI 思考中")

            # 显示AI调用步骤
            self.console.print(f"[dim]📝 AI调用状态: {state_text}[/dim]")

            with Status(f"[bold yellow]{state_text}[/bold yellow]", console=self.console):
                # 根据状态调整参数
                temperature = 0.7
                max_tokens = 2000
                if state.value == "code_gen":
                    temperature = 0.3
                    max_tokens = 4000
                    self.console.print("[dim]📝 代码生成模式: 温度=0.3, 最大token=4000[/dim]")

                # 获取当前模型配置
                current_config = self.llm_client.get_current_config()
                if not current_config:
                    self.console.print("[yellow]⚠️  未找到当前模型配置[/yellow]")
                    return None

                if current_config:
                    temperature = current_config.temperature
                    max_tokens = current_config.max_tokens
                    self.console.print(f"[dim]📝 模型配置: {current_config.name}, 温度={temperature}, 最大token={max_tokens}[/dim]")

                try:
                    # 显示API调用信息
                    self.console.print(f"[dim]📝 发送API请求: {len(messages)} 条消息[/dim]")

                    # 调用API
                    response = self.llm_client.chat_completion(
                        messages=messages,
                        stream=True,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )

                    # 流式显示响应
                    self.console.print("[dim]📝 开始接收流式响应...[/dim]")
                    return self._stream_response(response)

                except UnicodeError as e:
                    # 编码相关错误
                    self.console.print(f"[yellow]⚠️  编码错误: {e}[/yellow]")
                    self.console.print("[dim]尝试使用非流式请求...[/dim]")

                    # 回退到非流式请求
                    return self._fallback_non_streaming_call(messages, temperature, max_tokens)

        except Exception as e:
            self.console.print(f"[red]❌ AI调用失败: {e}[/red]")
            self.conversation.record_error()
            # 提供帮助建议
            self._suggest_solutions(e)
            return None

    def _show_welcome(self, mode: str):
        """显示欢迎信息"""
        current_config = self.llm_client.get_current_config()
        model_info = current_config.name if current_config else "未知"

        # 获取上下文状态
        has_context = self.conversation.has_saved_context(self.project_root) if self.project_root else False
        context_status = "[green]已加载[/green]" if has_context else "[yellow]新对话[/yellow]"

        # 获取对话统计
        stats = self.conversation.get_statistics()
        message_count = stats['total_messages']

        welcome_text = f"""
[bold]🚀 DefineX AI 助手已就绪！[/bold]

[dim]模型:[/dim] {model_info}
[dim]模式:[/dim] {'[bold green]编码模式[/bold green]' if mode == 'code' else '[bold blue]对话模式[/bold blue]'}
[dim]项目:[/dim] {self.project_root}
[dim]上下文:[/dim] {context_status} ({message_count} 条消息)
[dim]历史优化:[/dim] [green]启用[/green]

[bold]💡 可用命令:[/bold]
  • help - 显示帮助
  • save-context - 保存当前对话上下文
  • load-context <hash> - 加载特定上下文
  • list-contexts - 列出所有上下文
  • clear-context - 清除当前上下文

[bold yellow]✨ 开始您的插件开发之旅吧！[/bold yellow]
"""

        panel = Panel(
            welcome_text,
            title="AI 助手",
            border_style="cyan"
        )
        self.console.print(panel)

    def switch_model(self, model_name: str) -> bool:
        """切换AI模型"""
        try:
            if self.llm_client.set_current_model(model_name):
                self.current_model = model_name

                # 更新配置
                llm_config = self.config_mgr.get_llm_config()
                llm_config.current_model = model_name
                self.config_mgr.save_llm_config(llm_config)

                self.console.print(f"[green]✅ 已切换到模型: {model_name}[/green]")
                return True
            else:
                self.console.print(f"[red]❌ 切换模型失败: {model_name} 不可用[/red]")
                return False

        except Exception as e:
            self.console.print(f"[red]❌ 切换模型失败: {e}[/red]")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "is_running": self.is_running,
            "project_root": str(self.project_root) if self.project_root else None,
            "current_model": self.current_model,
            "has_current_code": self.conversation.current_code is not None,
            "conversation_stats": self.conversation.get_statistics()
        }

    def chat(self, root_path: str|Path, mode: str = "code", console: Optional[Console] = None):
        """
        便捷函数：与项目进行AI对话

        Args:
            root_path: 项目根目录
            mode: 对话模式（"code" 或 "chat"）
            console: Rich控制台实例
        """
        if self.initialize_project(root_path):
            self.start_chat(mode)
        else:
            console.print("[red]❌ 无法初始化项目[/red]")

    def _stream_response(self, response_stream) -> str:
        """优化的流式响应处理 - 移除rich.live，使用更稳定的显示方案"""
        full_response = ""

        # 显示响应开始标记
        self.console.print("[bold cyan]🤖 AI 回答开始:[/bold cyan]\n")

        try:
            buffer = ""
            char_count = 0
            line_count = 0

            for chunk in response_stream:
                if chunk.choices[0].delta.content is not None:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        # 使用安全的文本处理
                        safe_delta = self.text_cleaner.clean_unicode(delta, "normalize")
                        if safe_delta:
                            buffer += safe_delta
                            full_response += safe_delta
                            char_count += len(safe_delta)

                            # 统计行数
                            if '\n' in safe_delta:
                                line_count += safe_delta.count('\n')

                            # 安全显示 - 使用较小的缓冲阈值
                            if len(buffer) > 20:  # 降低缓冲阈值，提高响应速度
                                safe_buffer = self.text_cleaner.safe_markdown(buffer)
                                # 直接打印，不使用live
                                self.console.print(safe_buffer, end="", style="white")
                                buffer = ""

            # 显示剩余内容
            if buffer:
                safe_buffer = self.text_cleaner.safe_markdown(buffer)
                self.console.print(safe_buffer, end="", style="white")

            # 显示响应结束标记和统计信息
            self.console.print()
            self.console.print(f"\n[dim]📊 响应统计: {char_count} 字符, {line_count} 行[/dim]")
            self.console.print("[bold green]✅ AI 回答结束[/bold green]\n")

        except Exception as e:
            self.console.print(f"[yellow]⚠️  流式显示错误: {e}[/yellow]")
            # 直接输出已收集的文本
            if full_response:
                safe_response = self.text_cleaner.clean_unicode(full_response, "normalize")
                self.console.print("\n[bold]🤖 AI 回答（完整）:[/bold]\n")
                self.console.print(safe_response)
            else:
                self.console.print("[red]❌ 未收到任何响应内容[/red]")

        # 最后清理整个响应
        return self.text_cleaner.clean_unicode(full_response, "normalize")


    def _fallback_non_streaming_call(self, messages, temperature, max_tokens) -> str:
        """回退到非流式请求"""
        try:
            # 非流式请求
            response = self.llm_client.chat_completion(
                messages=messages,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            if content:
                # 清理响应
                safe_content = self.text_cleaner.clean_unicode(content, "ignore")
                self.console.print("\n[bold]🤖 AI 回答:[/bold]\n")
                self.console.print(safe_content)
                return safe_content

            return ""

        except Exception as e:
            self.console.print(f"[red]❌ 非流式请求也失败: {e}[/red]")
            return ""

    def _suggest_solutions(self, error):
        """根据错误提供解决方案建议"""
        error_str = str(error).lower()

        if "utf-8" in error_str or "surrogate" in error_str:
            self.console.print("[yellow]💡 解决方案：[/yellow]")
            self.console.print("1. 尝试使用不同的AI模型")
            self.console.print("2. 简化您的输入描述")
            self.console.print("3. 避免使用特殊字符或表情符号")

        elif "authentication" in error_str or "401" in error_str:
            self.console.print("[yellow]💡 解决方案：[/yellow]")
            self.console.print("1. 检查API Key是否正确")
            self.console.print("2. 确认base_url配置正确")
            self.console.print("3. 检查API Key是否有足够的余额或权限")

        elif "timeout" in error_str:
            self.console.print("[yellow]💡 解决方案：[/yellow]")
            self.console.print("1. 检查网络连接")
            self.console.print("2. 增加超时时间设置")
            self.console.print("3. 简化请求内容")

    # ===== 上下文管理方法 =====

    def _try_load_context(self):
        """尝试加载保存的上下文"""
        try:
            if self.project_root and self.conversation.has_saved_context(self.project_root):
                with Status("正在加载对话上下文...", console=self.console):
                    success = self.conversation.load_context(self.project_root)
                    if success:
                        stats = self.conversation.get_statistics()
                        self.console.print(f"[green]✓ 已加载上下文: {stats['total_messages']} 条消息[/green]")
                    else:
                        self.console.print("[yellow]⚠️  上下文加载失败或不存在[/yellow]")
        except Exception as e:
            self.console.print(f"[yellow]⚠️  上下文加载异常: {e}[/yellow]")

    def _display_context_status(self):
        """显示上下文状态"""
        if self.project_root:
            has_context = self.conversation.has_saved_context(self.project_root)
            if has_context:
                stats = self.conversation.get_statistics()
                self.console.print(f"[dim]📚 上下文: 已加载 {stats['total_messages']} 条历史消息[/dim]")
            else:
                self.console.print("[dim]📚 上下文: 无历史记录，开始新对话[/dim]")

    def save_current_context(self) -> bool:
        """保存当前上下文"""
        try:
            if not self.project_root:
                self.console.print("[red]❌ 请先初始化项目[/red]")
                return False

            with Status("正在保存对话上下文...", console=self.console):
                file_path = self.conversation.save_context(self.project_root)
                stats = self.conversation.get_statistics()
                self.console.print(f"[green]✅ 上下文已保存到: {file_path}[/green]")
                self.console.print(f"[dim]  包含 {stats['total_messages']} 条消息，{stats['total_tokens']} tokens[/dim]")
                return True

        except Exception as e:
            self.console.print(f"[red]❌ 保存上下文失败: {e}[/red]")
            return False

    def load_specific_context(self, context_hash: str) -> bool:
        """加载特定的上下文"""
        try:
            # 查找对应的上下文文件
            context_dir = self.conversation.get_context_dir()
            file_path = context_dir / f"context_{context_hash}.json"

            if not file_path.exists():
                self.console.print(f"[red]❌ 找不到上下文文件: {context_hash}[/red]")
                return False

            with Status("正在加载指定上下文...", console=self.console):
                # 使用基础的load_from_file方法
                self.conversation.load_from_file(file_path)
                stats = self.conversation.get_statistics()
                self.console.print(f"[green]✅ 已加载上下文: {stats['total_messages']} 条消息[/green]")
                return True

        except Exception as e:
            self.console.print(f"[red]❌ 加载上下文失败: {e}[/red]")
            return False

    def list_all_contexts(self):
        """列出所有保存的上下文"""
        try:
            contexts = self.conversation.list_contexts()

            if not contexts:
                self.console.print("[yellow]📭 没有保存的上下文[/yellow]")
                return

            self.console.print("[bold]📚 保存的上下文列表:[/bold]")
            for i, ctx in enumerate(contexts, 1):
                project_path = ctx.get("project_path", "未知项目")
                saved_at = ctx.get("saved_at", "未知时间")
                messages = ctx.get("total_messages", 0)
                tokens = ctx.get("total_tokens", 0)

                self.console.print(f"  {i}. [cyan]{ctx['file']}[/cyan]")
                self.console.print(f"     项目: {project_path}")
                self.console.print(f"     时间: {saved_at}")
                self.console.print(f"     消息: {messages} 条, {tokens} tokens")
                self.console.print()

        except Exception as e:
            self.console.print(f"[red]❌ 列出上下文失败: {e}[/red]")

    def clear_current_context(self, delete_all: bool = False) -> bool:
        """
        清除上下文

        Args:
            delete_all: 是否删除所有上下文（不仅仅是当前项目）

        Returns:
            是否成功
        """
        try:
            if delete_all:
                # 确认操作
                confirm = Confirm.ask("[bold red]⚠️  确认删除所有保存的上下文？[/bold red]", default=False)
                if not confirm:
                    self.console.print("[yellow]操作已取消[/yellow]")
                    return False

                # 删除所有上下文
                result = self.conversation.delete_context(delete_all=True)

                if result["success"]:
                    deleted_count = result.get("deleted_count", 0)
                    failed_count = result.get("failed_count", 0)

                    self.console.print(f"[green]✅ 已删除所有上下文: {deleted_count} 个文件[/green]")
                    if failed_count > 0:
                        self.console.print(f"[yellow]⚠️  有 {failed_count} 个文件删除失败[/yellow]")

                    # 清空内存中的对话历史
                    self.conversation.clear_history(keep_system=True)
                    return True
                else:
                    self.console.print(f"[red]❌ 删除失败: {result.get('error', '未知错误')}[/red]")
                    return False
            else:
                # 只删除当前项目的上下文
                if not self.project_root:
                    self.console.print("[red]❌ 请先初始化项目[/red]")
                    return False

                # 确认操作
                confirm = Confirm.ask("[bold yellow]确认清除当前项目的上下文？[/bold yellow]", default=False)
                if not confirm:
                    self.console.print("[yellow]操作已取消[/yellow]")
                    return False

                result = self.conversation.delete_context(self.project_root)

                if result["success"]:
                    self.console.print(f"[green]✅ {result.get('message', '已清除当前项目的上下文')}[/green]")
                    # 同时清空内存中的对话历史
                    self.conversation.clear_history(keep_system=True)
                    return True
                else:
                    error_msg = result.get('error', '未知错误')
                    if "文件不存在" in error_msg:
                        self.console.print("[yellow]⚠️  当前项目没有保存的上下文[/yellow]")
                        # 仍然清空内存中的对话历史
                        self.conversation.clear_history(keep_system=True)
                        return True
                    else:
                        self.console.print(f"[red]❌ 清除上下文失败: {error_msg}[/red]")
                        return False

        except Exception as e:
            self.console.print(f"[red]❌ 清除上下文失败: {e}[/red]")
            return False

    def auto_save_context(self):
        """自动保存上下文（在对话结束时调用）"""
        try:
            if self.project_root and self.conversation.messages:
                # 只有在有对话历史时才保存
                stats = self.conversation.get_statistics()
                if stats['total_messages'] > 1:  # 至少有1条用户消息
                    self.save_current_context()
        except:
            pass  # 自动保存失败时不中断主流程

    def stop(self):
        """停止引擎（重写以包含自动保存）"""
        # 自动保存上下文
        self.auto_save_context()

        self.is_running = False
        self.console.print("[yellow]👋 AI助手已停止[/yellow]")

    # ===== 自动化需求处理方法 =====

    def _is_requirement_description(self, user_input: str) -> bool:
        """
        判断用户输入是否是需求描述

        规则：
        1. 长度超过20个字符
        2. 包含开发相关的关键词
        3. 不是命令
        """
        # 如果是命令，直接返回False
        if self.commands.is_command(user_input):
            return False

        # 检查长度
        if len(user_input) < 20:
            return False

        # 检查是否包含开发相关关键词
        development_keywords = [
            "开发", "实现", "创建", "构建", "设计", "编写", "制作",
            "插件", "功能", "模块", "系统", "应用", "程序", "工具",
            "需要", "想要", "希望", "需求", "要求", "规格", "spec"
        ]

        user_input_lower = user_input.lower()
        keyword_count = sum(1 for keyword in development_keywords if keyword in user_input_lower)

        # 如果包含至少2个开发关键词，认为是需求描述
        return keyword_count >= 2

    def _generate_todo_from_requirements(self, requirements: str):
        """从需求生成TODO"""
        try:
            if not self.project_root:
                self.console.print("[red]❌ 无法生成TODO：项目未初始化[/red]")
                return

            # 准备项目信息
            project_info = {
                "name": self.project_root.name,
                "path": str(self.project_root)
            }

            # 生成TODO任务
            with Status("正在生成TODO任务列表...", console=self.console):
                tasks = self.todo_generator.generate_from_requirements(requirements, project_info)

            # 保存TODO到文件
            todo_file = self.project_root / "TODO.md"
            success = self.todo_generator.save_to_file(todo_file)

            if success:
                # 显示TODO
                todo_display = self.todo_generator.format_for_display()
                self.console.print("\n[bold green]✅ TODO任务已生成:[/bold green]")
                self.console.print(todo_display)
                self.console.print(f"\n[dim]📄 详细TODO已保存到: {todo_file}[/dim]")
            else:
                self.console.print("[red]❌ 保存TODO失败[/red]")

        except Exception as e:
            self.console.print(f"[red]❌ 生成TODO失败: {e}[/red]")

    def _auto_start_code_flow(self, requirements: str):
        """自动启动代码生成流程"""
        try:
            if not self.project_root:
                self.console.print("[red]❌ 无法启动流程：项目未初始化[/red]")
                return

            # 导入流程管理器
            from .code_flow_manager import CodeFlowManager

            # 初始化流程管理器
            flow_manager = CodeFlowManager(
                project_path=str(self.project_root),
                project_name=self.project_root.name
            )

            # 启动流程
            with Status("正在启动代码生成流程...", console=self.console):
                result = flow_manager.start_flow(requirements)

            if result["success"]:
                self.console.print(f"[green]✅ 代码生成流程已启动[/green]")
                self.console.print(f"[dim]当前阶段: {result.get('current_stage', '需求分析')}[/dim]")

                # 显示流程状态
                status = flow_manager.get_flow_status()
                self.console.print(f"[dim]进度: {status['progress']:.1f}%[/dim]")

                # 保存流程管理器到上下文
                self._flow_manager = flow_manager

                # 提示用户下一步
                self.console.print("\n[bold cyan]💡 下一步:[/bold cyan]")
                self.console.print("1. 使用 'flow-status' 查看流程状态")
                self.console.print("2. 使用 'next-stage' 进入下一阶段")
                self.console.print("3. 继续描述需求细节")
            else:
                self.console.print(f"[red]❌ 启动流程失败: {result.get('error', '未知错误')}[/red]")

        except Exception as e:
            self.console.print(f"[red]❌ 启动代码流程失败: {e}[/red]")

    def get_todo_summary(self) -> str:
        """获取TODO摘要"""
        try:
            if not self.project_root:
                return "项目未初始化"

            todo_file = self.project_root / "TODO.md"
            if not todo_file.exists():
                return "暂无TODO任务"

            # 加载TODO
            self.todo_generator.load_from_file(todo_file)
            return self.todo_generator.format_for_display()

        except Exception as e:
            return f"获取TODO失败: {e}"

    def update_todo_progress(self, task_index: int, completed: bool = True):
        """更新TODO进度"""
        try:
            if not self.project_root:
                self.console.print("[red]❌ 无法更新TODO：项目未初始化[/red]")
                return False

            todo_file = self.project_root / "TODO.md"
            if not todo_file.exists():
                self.console.print("[yellow]⚠️  没有找到TODO文件[/yellow]")
                return False

            # 加载TODO
            self.todo_generator.load_from_file(todo_file)

            # 更新任务状态
            if 0 <= task_index < len(self.todo_generator.tasks):
                task = self.todo_generator.tasks[task_index]
                if completed:
                    task.mark_completed()
                else:
                    task.completed = False
                    task.completed_at = None

                # 保存更新
                self.todo_generator.save_to_file(todo_file)

                status = "完成" if completed else "重置"
                self.console.print(f"[green]✅ 任务 '{task.title}' 已标记为{status}[/green]")
                return True
            else:
                self.console.print(f"[red]❌ 无效的任务索引: {task_index}[/red]")
                return False

        except Exception as e:
            self.console.print(f"[red]❌ 更新TODO失败: {e}[/red]")
            return False
