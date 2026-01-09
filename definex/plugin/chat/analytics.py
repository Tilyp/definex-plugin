"""
DefineX 数据统计模块
提供详细的对话统计、错误统计和性能指标
"""
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class ErrorType(Enum):
    """错误类型枚举"""
    API_ERROR = "api_error"           # API调用错误
    CONNECTION_ERROR = "connection_error"  # 连接错误
    PARSING_ERROR = "parsing_error"   # 解析错误
    ENCODING_ERROR = "encoding_error" # 编码错误
    VALIDATION_ERROR = "validation_error"  # 验证错误
    FILE_ERROR = "file_error"         # 文件操作错误
    UNKNOWN_ERROR = "unknown_error"   # 未知错误


class CommandCategory(Enum):
    """命令分类枚举"""
    SYSTEM = "system"          # 系统命令（help, exit等）
    CODE = "code"              # 代码相关命令
    CONTEXT = "context"        # 上下文命令
    STATS = "stats"            # 统计命令
    CONFIG = "config"          # 配置命令
    TEST = "test"              # 测试命令


@dataclass
class TokenUsage:
    """Token使用统计"""
    prompt_tokens: int = 0      # 输入Token
    completion_tokens: int = 0  # 输出Token
    total_tokens: int = 0       # 总Token

    def add_usage(self, prompt: int, completion: int) -> None:
        """添加Token使用"""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion

    def to_dict(self) -> Dict[str, int]:
        """转换为字典"""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }


@dataclass
class ErrorStats:
    """错误统计"""
    total_errors: int = 0
    error_counts: Dict[ErrorType, int] = field(default_factory=lambda: defaultdict(int))
    last_error_time: Optional[datetime] = None
    last_error_type: Optional[ErrorType] = None
    last_error_message: Optional[str] = None

    def record_error(self, error_type: ErrorType, message: str = "") -> None:
        """记录错误"""
        self.total_errors += 1
        self.error_counts[error_type] += 1
        self.last_error_time = datetime.now()
        self.last_error_type = error_type
        self.last_error_message = message

    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        return {
            "total_errors": self.total_errors,
            "error_distribution": {k.value: v for k, v in self.error_counts.items()},
            "last_error": {
                "time": self.last_error_time.isoformat() if self.last_error_time else None,
                "type": self.last_error_type.value if self.last_error_type else None,
                "message": self.last_error_message
            }
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_api_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_response_time: float = 0.0  # 总响应时间（秒）
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    avg_response_time: float = 0.0

    def record_call(self, success: bool, response_time: float) -> None:
        """记录API调用"""
        self.total_api_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

        self.total_response_time += response_time
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        self.avg_response_time = self.total_response_time / self.total_api_calls

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            "total_calls": self.total_api_calls,
            "success_rate": self.successful_calls / self.total_api_calls if self.total_api_calls > 0 else 0,
            "response_time": {
                "total": f"{self.total_response_time:.2f}s",
                "average": f"{self.avg_response_time:.2f}s",
                "min": f"{self.min_response_time:.2f}s" if self.min_response_time != float('inf') else "N/A",
                "max": f"{self.max_response_time:.2f}s"
            }
        }


@dataclass
class CommandStats:
    """命令使用统计"""
    total_commands: int = 0
    command_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    category_counts: Dict[CommandCategory, int] = field(default_factory=lambda: defaultdict(int))
    last_command_time: Optional[datetime] = None
    last_command_name: Optional[str] = None

    def record_command(self, command_name: str, category: CommandCategory) -> None:
        """记录命令使用"""
        self.total_commands += 1
        self.command_counts[command_name] += 1
        self.category_counts[category] += 1
        self.last_command_time = datetime.now()
        self.last_command_name = command_name

    def get_top_commands(self, limit: int = 5) -> List[Tuple[str, int]]:
        """获取最常用的命令"""
        sorted_commands = sorted(
            self.command_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_commands[:limit]

    def get_command_summary(self) -> Dict[str, Any]:
        """获取命令摘要"""
        return {
            "total_commands": self.total_commands,
            "top_commands": self.get_top_commands(5),
            "category_distribution": {k.value: v for k, v in self.category_counts.items()},
            "last_command": {
                "time": self.last_command_time.isoformat() if self.last_command_time else None,
                "name": self.last_command_name
            }
        }


@dataclass
class CodeGenerationStats:
    """代码生成统计"""
    total_generations: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    total_lines_generated: int = 0
    files_created: int = 0
    files_updated: int = 0

    def record_generation(self, success: bool, lines_generated: int = 0,
                         file_created: bool = False, file_updated: bool = False) -> None:
        """记录代码生成"""
        self.total_generations += 1
        if success:
            self.successful_generations += 1
            self.total_lines_generated += lines_generated
            if file_created:
                self.files_created += 1
            if file_updated:
                self.files_updated += 1
        else:
            self.failed_generations += 1

    def get_code_summary(self) -> Dict[str, Any]:
        """获取代码生成摘要"""
        return {
            "total_generations": self.total_generations,
            "success_rate": self.successful_generations / self.total_generations if self.total_generations > 0 else 0,
            "total_lines": self.total_lines_generated,
            "average_lines": self.total_lines_generated / self.successful_generations if self.successful_generations > 0 else 0,
            "files_created": self.files_created,
            "files_updated": self.files_updated
        }


@dataclass
class AnalyticsData:
    """分析数据容器"""
    # 基础统计
    session_start_time: datetime = field(default_factory=datetime.now)
    session_duration: float = 0.0

    # 详细统计
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    error_stats: ErrorStats = field(default_factory=ErrorStats)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    command_stats: CommandStats = field(default_factory=CommandStats)
    code_generation_stats: CodeGenerationStats = field(default_factory=CodeGenerationStats)

    # 模型使用统计
    model_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    current_model: Optional[str] = None

    def update_session_duration(self) -> None:
        """更新会话持续时间"""
        self.session_duration = (datetime.now() - self.session_start_time).total_seconds()

    def record_model_usage(self, model_name: str) -> None:
        """记录模型使用"""
        self.model_usage[model_name] += 1
        self.current_model = model_name

    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """获取综合摘要"""
        self.update_session_duration()

        return {
            "session": {
                "start_time": self.session_start_time.isoformat(),
                "duration": f"{self.session_duration:.1f}s",
                "current_model": self.current_model
            },
            "tokens": self.token_usage.to_dict(),
            "errors": self.error_stats.get_error_summary(),
            "performance": self.performance_metrics.get_performance_summary(),
            "commands": self.command_stats.get_command_summary(),
            "code_generation": self.code_generation_stats.get_code_summary(),
            "model_usage": dict(self.model_usage)
        }

    def save_to_file(self, file_path: Path) -> bool:
        """保存数据到文件"""
        try:
            data = self.get_comprehensive_summary()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存分析数据失败: {e}")
            return False

    def load_from_file(self, file_path: Path) -> bool:
        """从文件加载数据"""
        try:
            if not file_path.exists():
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 这里可以添加从文件恢复数据的逻辑
            # 由于数据结构复杂，暂时只支持保存，不支持完整恢复
            return True
        except Exception as e:
            print(f"加载分析数据失败: {e}")
            return False

    def reset(self) -> None:
        """重置所有统计"""
        self.__init__()  # 重新初始化所有字段
