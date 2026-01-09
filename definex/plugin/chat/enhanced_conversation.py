"""
增强版对话历史管理器，集成详细的数据统计和分析功能
"""
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from definex.plugin.chat.analytics import (
    AnalyticsData, ErrorType, CommandCategory
)
from definex.plugin.chat.prompt_builder import (
    SystemPromptBuilder,
    PromptConfig,
    ConversationState
)
from definex.plugin.chat.text_utils import TextCleaner


class MessageRole(Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """消息数据类"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0  # 估算的token数
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tokens": self.tokens,
            "metadata": self.metadata
        }


class EnhancedConversationManager:
    """增强版对话历史管理器，集成详细的数据统计和分析功能"""

    def __init__(self, max_history_length: int = 10, max_tokens: int = 4000):
        self.max_history_length = max_history_length
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
        self.system_prompt: Optional[str] = None
        self._total_tokens = 0
        self.system_context: Optional[str] = None
        self.project_context: Optional[str] = None
        self.code_summary: Dict[str, str] = {}
        self._estimated_tokens = 0
        self.text_cleaner = TextCleaner()

        # 创建提示词构建器
        self.prompt_builder = SystemPromptBuilder()
        self.current_code: Optional[str] = None

        # 状态跟踪
        self.conversation_state = ConversationState.INITIAL

        # 分析数据
        self.analytics = AnalyticsData()

        # API调用跟踪
        self._last_api_call_start: Optional[float] = None
        self._current_model: Optional[str] = None

    def add_message(self, role: MessageRole, content: str, metadata: Dict[str, Any] = None) -> Message:
        """添加消息到历史，包含编码清理和统计"""
        # 清理内容
        cleaned_content = self.text_cleaner.clean_unicode(content, "ignore")
        message = Message(
            role=role,
            content=cleaned_content,
            metadata=metadata or {}
        )
        message.tokens = self._estimate_tokens(cleaned_content)

        self.messages.append(message)
        self._total_tokens += message.tokens

        # 如果超出限制，移除旧消息
        self._trim_conversation()

        return message

    def get_messages_for_api(self, user_input: str) -> List[Dict[str, str]]:
        """获取用于API的消息列表，记录API调用开始时间"""
        self._last_api_call_start = time.time()

        messages = []

        # 1. 系统提示词
        system_prompt = self.get_system_prompt(user_input)
        # 清理内容
        cleaned_content = self.text_cleaner.clean_unicode(system_prompt, "ignore")
        messages.append({"role": "system", "content": cleaned_content})

        # 2. 历史消息（如果有）
        if len(self.messages) > 1:
            # 添加最近的历史消息
            recent = self.messages[-4:]  # 最近4条
            for msg in recent:
                if msg.role != "system":  # 不重复系统消息
                    messages.append(msg)

        # 3. 当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def record_api_response(self, response: Dict[str, Any], model_name: str) -> None:
        """记录API响应，更新统计信息"""
        if self._last_api_call_start is None:
            return

        response_time = time.time() - self._last_api_call_start
        self._last_api_call_start = None

        # 记录模型使用
        self._current_model = model_name
        self.analytics.record_model_usage(model_name)

        # 记录性能指标
        success = "error" not in response
        self.analytics.performance_metrics.record_call(success, response_time)

        # 记录Token使用
        if success and "usage" in response:
            usage = response["usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            self.analytics.token_usage.add_usage(prompt_tokens, completion_tokens)

        # 记录错误
        if not success:
            self.analytics.error_stats.record_error(
                ErrorType.API_ERROR,
                response.get("error", "未知API错误")
            )

        # 提取并记录代码生成
        if success and "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0].get("message", {}).get("content", "")
            if content:
                code_blocks = self.extract_code_blocks(content)
                if code_blocks:
                    lines_generated = sum(len(code.split('\n')) for code in code_blocks)
                    self.analytics.code_generation_stats.record_generation(
                        success=True,
                        lines_generated=lines_generated
                    )

    def set_system_prompt(self, prompt: str):
        """设置系统提示词"""
        self.system_prompt = prompt

    def set_project_context(self, context: str):
        """设置项目上下文"""
        self.project_context = self._compress_context(context)

    def _compress_context(self, context: str) -> str:
        """压缩上下文"""
        lines = context.split('\n')
        compressed = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(marker in line for marker in ["项目根目录", "📁", "📄", "✅", "⚠️"]):
                compressed.append(line)

        return "\n".join(compressed) if compressed else "项目上下文已加载"

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的token数量"""
        # 简单估算：英文大约4字符=1token，中文大约2字符=1token
        # 这里使用平均估算：3字符=1token
        return max(1, len(text) // 3)

    def _trim_conversation(self):
        """修剪对话历史，确保不超过限制"""
        if not self.messages:
            return

        # 查找系统消息索引
        system_indices = [i for i, msg in enumerate(self.messages) if msg.role == MessageRole.SYSTEM]
        if not system_indices:
            return

        first_system_idx = system_indices[0]

        # 移除最早的非系统消息，直到满足限制
        while (self._total_tokens > self.max_tokens or
               len(self.messages) > self.max_history_length) and \
                len(self.messages) > first_system_idx + 1:

            removed = self.messages.pop(first_system_idx + 1)
            self._total_tokens -= removed.tokens

    def get_conversation_summary(self, max_messages: int = 3) -> str:
        """获取对话摘要"""
        if not self.messages:
            return "对话历史为空"

        summary = []
        recent_messages = self.messages[-max_messages:]

        for msg in recent_messages:
            role_name = "系统" if msg.role == MessageRole.SYSTEM else \
                "用户" if msg.role == MessageRole.USER else "助手"

            content_preview = msg.content[:80]
            if len(msg.content) > 80:
                content_preview += "..."

            summary.append(f"{role_name}: {content_preview}")

        return "\n".join(summary)

    def get_system_prompt(self, user_input: str) -> str:
        """获取系统提示词"""
        # 分析对话状态
        self.conversation_state = self.prompt_builder.analyze_state(
            user_input, self.current_code is not None
        )

        # 准备上下文变量
        context_vars = {
            "project_context": self.project_context,
            "conversation_summary": self.get_conversation_summary(),
            "user_input": user_input
        }

        if self.current_code:
            context_vars["current_code"] = self.current_code

        # 根据状态选择配置
        if self.conversation_state == ConversationState.INITIAL:
            config = self.prompt_builder.get_initial_config()
        elif self.conversation_state == ConversationState.CHAT:
            config = self.prompt_builder.get_chat_config()
        else:
            # 其他状态使用自定义配置
            config = PromptConfig(
                state=self.conversation_state,
                include_project_context=self.conversation_state in [ConversationState.CODE_GENERATION, ConversationState.INITIAL],
                include_conversation_summary=self.conversation_state != ConversationState.INITIAL,
                include_code_examples=self.conversation_state in [ConversationState.CODE_GENERATION, ConversationState.INITIAL],
                include_error_handling=self.analytics.error_stats.total_errors > 0
            )

        # 构建提示词
        return self.prompt_builder.build(config, context_vars)

    def extract_code_blocks(self, content: str) -> List[str]:
        """提取代码块"""
        if not content:
            return []

        code_blocks = []

        # 1. 尝试标准的三重反引号格式
        standard_pattern = r'```(?:python|py)?\s*\n(.*?)\n\s*```'
        matches = re.findall(standard_pattern, content, re.DOTALL | re.IGNORECASE)

        if matches:
            for match in matches:
                code = match.strip()
                if code:
                    code_blocks.append(code)
            return code_blocks

        # 2. 尝试更宽松的匹配
        relaxed_pattern = r'```(?:python|py)?\s*(.*?)\s*```'
        relaxed_matches = re.findall(relaxed_pattern, content, re.DOTALL | re.IGNORECASE)

        for match in relaxed_matches:
            code = match.strip()
            if code:
                lines = code.split('\n')
                if len(lines) > 1 or 'def ' in code or 'class ' in code or 'import ' in code:
                    code_blocks.append(code)

        return code_blocks

    def get_basic_statistics(self) -> Dict[str, Any]:
        """获取基础对话统计信息"""
        stats = {
            "total_messages": len(self.messages),
            "total_tokens": self._total_tokens,
            "user_messages": sum(1 for msg in self.messages if msg.role == MessageRole.USER),
            "assistant_messages": sum(1 for msg in self.messages if msg.role == MessageRole.ASSISTANT),
            "system_messages": sum(1 for msg in self.messages if msg.role == MessageRole.SYSTEM),
            "average_tokens_per_message": self._total_tokens / len(self.messages) if self.messages else 0
        }

        return stats

    def get_detailed_statistics(self) -> Dict[str, Any]:
        """获取详细的统计信息"""
        return self.analytics.get_comprehensive_summary()

    def record_command(self, command_name: str, category: CommandCategory) -> None:
        """记录命令使用"""
        self.analytics.command_stats.record_command(command_name, category)

    def record_error(self, error_type: ErrorType, message: str = "") -> None:
        """记录错误"""
        self.analytics.error_stats.record_error(error_type, message)

    def record_code_generation(self, success: bool, lines_generated: int = 0,
                              file_created: bool = False, file_updated: bool = False) -> None:
        """记录代码生成"""
        self.analytics.code_generation_stats.record_generation(
            success, lines_generated, file_created, file_updated
        )

    def save_to_file(self, file_path: Path):
        """保存对话历史到文件"""
        try:
            data = {
                "messages": [msg.to_dict() for msg in self.messages],
                "system_prompt": self.system_prompt,
                "project_context": self.project_context,
                "analytics": self.analytics.get_comprehensive_summary(),
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "total_messages": len(self.messages),
                    "total_tokens": self._total_tokens,
                    "current_model": self._current_model
                }
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"保存对话历史失败: {e}")

    def load_from_file(self, file_path: Path):
        """从文件加载对话历史"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载消息
            self.messages = []
            for msg_data in data.get("messages", []):
                message = Message(
                    role=MessageRole(msg_data["role"]),
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    tokens=msg_data.get("tokens", 0),
                    metadata=msg_data.get("metadata", {})
                )
                self.messages.append(message)

            # 加载其他数据
            self.system_prompt = data.get("system_prompt")
            self.project_context = data.get("project_context")
            self._total_tokens = sum(msg.tokens for msg in self.messages)

            # 注意：分析数据比较复杂，这里只加载基本信息
            # 完整的分析数据恢复需要更复杂的逻辑

        except Exception as e:
            raise Exception(f"加载对话历史失败: {e}")

    def set_current_code(self, code: str):
        """设置当前代码"""
        self.current_code = code

    def clear_history(self, keep_system: bool = True):
        """清空对话历史"""
        if keep_system:
            # 保留系统消息
            system_messages = [msg for msg in self.messages if msg.role == MessageRole.SYSTEM]
            self.messages = system_messages
            self._total_tokens = sum(msg.tokens for msg in system_messages)
        else:
            self.messages = []
            self._total_tokens = 0
        self.current_code = None
        self.conversation_state = ConversationState.INITIAL

    def reset_statistics(self) -> None:
        """重置所有统计信息"""
        self.analytics.reset()

    def export_statistics(self, file_path: Path) -> bool:
        """导出统计信息到文件"""
        return self.analytics.save_to_file(file_path)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（兼容旧版本）"""
        user_count = sum(1 for msg in self.messages if msg.role == MessageRole.USER)
        assistant_count = sum(1 for msg in self.messages if msg.role == MessageRole.ASSISTANT)

        return {
            "total_messages": len(self.messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "state": self.conversation_state.value,
            "error_count": self.analytics.error_stats.total_errors,
            "has_current_code": self.current_code is not None
        }
