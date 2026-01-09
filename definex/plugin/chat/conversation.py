"""
对话历史管理器，优化消息压缩和上下文管理
"""
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

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


class ConversationManager:
    """对话历史管理器，添加编码安全"""

    def __init__(self, max_history_length: int = 10, max_tokens: int = 4000):
        self.max_history_length = max_history_length
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
        self.system_prompt: Optional[str] = None
        self._total_tokens = 0
        self.system_context: Optional[str] = None
        self.project_context: Optional[str] = None
        self.messages: List[Message] = []
        self.code_summary: Dict[str, str] = {}
        self._estimated_tokens = 0
        self.error_count = 0
        self.text_cleaner = TextCleaner()
        # 创建提示词构建器
        self.prompt_builder = SystemPromptBuilder()
        self.current_code: Optional[str] = None

        # 状态跟踪
        self.conversation_state = ConversationState.INITIAL

    def add_message(self, role: MessageRole, content: str, metadata: Dict[str, Any] = None) -> Message:
        """添加消息到历史，包含编码清理"""
        # 清理内容
        cleaned_content = self.text_cleaner.clean_unicode(content, "ignore")
        message = Message(
            role=role,
            content=cleaned_content,
            metadata=metadata or {}
        )
        message.tokens = self._estimate_tokens(cleaned_content)

        self.messages.append(message)
        self._estimated_tokens += message.tokens

        # 如果超出限制，移除旧消息
        self._trim_conversation()

        return message

    def get_messages_for_api(self, user_input: str) -> List[Dict[str, str]]:
        """获取用于API的消息列表"""
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
                if msg.role != MessageRole.SYSTEM:  # 不重复系统消息
                    # 将Message对象转换为字典
                    messages.append({
                        "role": msg.role.value,
                        "content": msg.content
                    })

        # 3. 当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

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
                include_error_handling=self.error_count > 0
            )

        # 构建提示词
        return self.prompt_builder.build(config, context_vars)

    def extract_code_blocks(self, content: str) -> List[str]:
        """提取代码块 - 推荐版本"""
        if not content:
            return []

        code_blocks = []

        # 1. 尝试标准的三重反引号格式
        # 匹配 ```python 或 ```py 或 ``` 后接代码块
        standard_pattern = r'```(?:python|py)?\s*\n(.*?)\n\s*```'
        matches = re.findall(standard_pattern, content, re.DOTALL | re.IGNORECASE)

        if matches:
            for match in matches:
                code = match.strip()
                if code:
                    code_blocks.append(code)
            return code_blocks

        # 2. 尝试更宽松的匹配（可能没有换行）
        relaxed_pattern = r'```(?:python|py)?\s*(.*?)\s*```'
        relaxed_matches = re.findall(relaxed_pattern, content, re.DOTALL | re.IGNORECASE)

        for match in relaxed_matches:
            code = match.strip()
            if code:
                # 检查是否是有效的Python代码
                lines = code.split('\n')
                if len(lines) > 1 or 'def ' in code or 'class ' in code or 'import ' in code:
                    code_blocks.append(code)

        return code_blocks

    def get_statistics(self) -> Dict[str, Any]:
        """获取对话统计信息"""
        stats = {
            "total_messages": len(self.messages),
            "total_tokens": self._total_tokens,
            "user_messages": sum(1 for msg in self.messages if msg.role == MessageRole.USER),
            "assistant_messages": sum(1 for msg in self.messages if msg.role == MessageRole.ASSISTANT),
            "system_messages": sum(1 for msg in self.messages if msg.role == MessageRole.SYSTEM),
            "average_tokens_per_message": self._total_tokens / len(self.messages) if self.messages else 0
        }

        return stats

    def save_to_file(self, file_path: Path):
        """保存对话历史到文件"""
        try:
            data = {
                "messages": [msg.to_dict() for msg in self.messages],
                "system_prompt": self.system_prompt,
                "project_context": self.project_context,
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "total_messages": len(self.messages),
                    "total_tokens": self._total_tokens
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
            self.system_prompt = data.get("system_prompt")
            self.project_context = data.get("project_context")
            self._total_tokens = sum(msg.tokens for msg in self.messages)

        except Exception as e:
            raise Exception(f"加载对话历史失败: {e}")

    def set_current_code(self, code: str):
        """设置当前代码"""
        self.current_code = code

    def record_error(self):
        """记录错误"""
        self.error_count += 1

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
        self.error_count = 0
        self.conversation_state = ConversationState.INITIAL

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        user_count = sum(1 for msg in self.messages if msg.role == "user")
        assistant_count = sum(1 for msg in self.messages if msg.role == "assistant")

        return {
            "total_messages": len(self.messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "state": self.conversation_state.value,
            "error_count": self.error_count,
            "has_current_code": self.current_code is not None
        }

    # ===== 增强的上下文管理功能 =====

    def get_context_hash(self, project_path: Optional[Path] = None) -> str:
        """获取上下文哈希值，用于唯一标识"""
        if project_path:
            path_str = str(project_path.resolve())
        else:
            path_str = self.project_context or "default"

        # 使用项目路径和当前时间生成哈希
        hash_input = f"{path_str}_{datetime.now().strftime('%Y%m%d')}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:8]

    def get_context_filename(self, project_path: Optional[Path] = None) -> str:
        """获取上下文文件名"""
        context_hash = self.get_context_hash(project_path)
        return f"context_{context_hash}.json"

    def get_context_dir(self) -> Path:
        """获取上下文保存目录"""
        # 使用用户主目录下的 .definex/contexts 目录
        context_dir = Path.home() / ".definex" / "contexts"
        context_dir.mkdir(parents=True, exist_ok=True)
        return context_dir

    def save_context(self, project_path: Optional[Path] = None) -> Path:
        """保存完整上下文到文件"""
        try:
            context_dir = self.get_context_dir()
            filename = self.get_context_filename(project_path)
            file_path = context_dir / filename

            # 优化上下文
            optimized_messages = self._optimize_context()

            data = {
                "version": "1.0",
                "project_path": str(project_path) if project_path else None,
                "project_context": self.project_context,
                "system_prompt": self.system_prompt,
                "current_code": self.current_code,
                "conversation_state": self.conversation_state.value,
                "error_count": self.error_count,
                "messages": [msg.to_dict() for msg in optimized_messages],
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "total_messages": len(optimized_messages),
                    "total_tokens": sum(msg.tokens for msg in optimized_messages),
                    "context_hash": self.get_context_hash(project_path),
                    "optimized": True
                }
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return file_path

        except Exception as e:
            raise Exception(f"保存上下文失败: {e}")

    def load_context(self, project_path: Optional[Path] = None) -> bool:
        """从文件加载上下文"""
        try:
            context_dir = self.get_context_dir()
            filename = self.get_context_filename(project_path)
            file_path = context_dir / filename

            if not file_path.exists():
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查版本
            if data.get("version") != "1.0":
                raise Exception(f"不支持的上下文版本: {data.get('version')}")

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

            # 加载其他上下文信息
            self.project_context = data.get("project_context")
            self.system_prompt = data.get("system_prompt")
            self.current_code = data.get("current_code")
            self.error_count = data.get("error_count", 0)

            # 设置对话状态
            state_value = data.get("conversation_state", "initial")
            self.conversation_state = ConversationState(state_value)

            # 更新token计数
            self._total_tokens = sum(msg.tokens for msg in self.messages)

            return True

        except Exception as e:
            raise Exception(f"加载上下文失败: {e}")

    def _optimize_context(self) -> List[Message]:
        """优化上下文，移除冗余信息"""
        if not self.messages:
            return []

        optimized = []

        # 1. 保留所有系统消息
        system_messages = [msg for msg in self.messages if msg.role == MessageRole.SYSTEM]
        optimized.extend(system_messages)

        # 2. 保留最近的对话（最多保留最近10条非系统消息）
        non_system_messages = [msg for msg in self.messages if msg.role != MessageRole.SYSTEM]
        recent_messages = non_system_messages[-10:] if len(non_system_messages) > 10 else non_system_messages

        # 3. 压缩长消息
        for msg in recent_messages:
            if len(msg.content) > 500:  # 长消息进行压缩
                compressed_msg = self._compress_message(msg)
                optimized.append(compressed_msg)
            else:
                optimized.append(msg)

        return optimized

    def _compress_message(self, message: Message) -> Message:
        """压缩单个消息"""
        content = message.content

        # 如果是代码消息，保留代码块
        if '```' in content:
            # 提取代码块
            code_blocks = self.extract_code_blocks(content)
            if code_blocks:
                # 保留代码块，压缩其他文本
                compressed_content = f"[压缩消息 - 包含 {len(code_blocks)} 个代码块]\n"
                for i, code in enumerate(code_blocks, 1):
                    compressed_content += f"\n代码块 {i}:\n```python\n{code[:200]}...\n```\n"
                message.content = compressed_content
                message.tokens = self._estimate_tokens(compressed_content)
        else:
            # 普通文本消息，保留开头和结尾
            if len(content) > 500:
                compressed = content[:200] + "\n...\n" + content[-200:]
                message.content = compressed
                message.tokens = self._estimate_tokens(compressed)

        return message

    def has_saved_context(self, project_path: Optional[Path] = None) -> bool:
        """检查是否有保存的上下文"""
        try:
            context_dir = self.get_context_dir()
            filename = self.get_context_filename(project_path)
            file_path = context_dir / filename
            return file_path.exists()
        except:
            return False

    def list_contexts(self) -> List[Dict[str, Any]]:
        """列出所有保存的上下文"""
        contexts = []
        context_dir = self.get_context_dir()

        for file_path in context_dir.glob("context_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                contexts.append({
                    "file": file_path.name,
                    "project_path": data.get("project_path"),
                    "saved_at": data.get("metadata", {}).get("saved_at"),
                    "total_messages": data.get("metadata", {}).get("total_messages", 0),
                    "total_tokens": data.get("metadata", {}).get("total_tokens", 0)
                })
            except:
                continue

        return contexts

    def delete_context(self, project_path: Optional[Path] = None, delete_all: bool = False) -> Dict[str, Any]:
        """
        删除保存的上下文

        Args:
            project_path: 项目路径，如果为None则删除所有上下文
            delete_all: 是否删除所有上下文

        Returns:
            删除结果统计
        """
        try:
            context_dir = self.get_context_dir()
            deleted_files = []
            failed_files = []

            if delete_all:
                # 删除所有上下文文件
                for file_path in context_dir.glob("context_*.json"):
                    try:
                        file_path.unlink()
                        deleted_files.append(file_path.name)
                    except Exception as e:
                        failed_files.append((file_path.name, str(e)))

                result = {
                    "success": True,
                    "deleted_count": len(deleted_files),
                    "failed_count": len(failed_files),
                    "deleted_files": deleted_files,
                    "failed_files": failed_files,
                    "message": f"已删除 {len(deleted_files)} 个上下文文件"
                }
            else:
                # 删除特定项目的上下文
                filename = self.get_context_filename(project_path)
                file_path = context_dir / filename

                if file_path.exists():
                    try:
                        file_path.unlink()
                        result = {
                            "success": True,
                            "deleted_count": 1,
                            "deleted_file": file_path.name,
                            "message": f"已删除上下文文件: {file_path.name}"
                        }
                    except Exception as e:
                        result = {
                            "success": False,
                            "error": f"删除文件失败: {e}",
                            "message": f"删除失败: {file_path.name}"
                        }
                else:
                    result = {
                        "success": False,
                        "error": "文件不存在",
                        "message": f"上下文文件不存在: {filename}"
                    }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"删除上下文失败: {e}"
            }

    def merge_contexts(self, contexts: List[Dict[str, Any]]) -> bool:
        """合并多个上下文"""
        try:
            # 按时间排序
            sorted_contexts = sorted(contexts,
                                   key=lambda x: x.get("metadata", {}).get("saved_at", ""))

            # 合并消息，去重
            all_messages = []
            seen_contents = set()

            for context in sorted_contexts:
                for msg_data in context.get("messages", []):
                    content = msg_data.get("content", "")
                    if content not in seen_contents:
                        seen_contents.add(content)
                        message = Message(
                            role=MessageRole(msg_data["role"]),
                            content=content,
                            timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                            tokens=msg_data.get("tokens", 0),
                            metadata=msg_data.get("metadata", {})
                        )
                        all_messages.append(message)

            # 更新当前上下文
            self.messages = all_messages
            self._total_tokens = sum(msg.tokens for msg in all_messages)

            return True

        except Exception as e:
            raise Exception(f"合并上下文失败: {e}")
