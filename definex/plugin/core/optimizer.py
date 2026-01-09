"""
DefineX 智能扫描优化器
支持根据用户意图进行代码检查和优化，排除不必要的文件/目录
"""
import fnmatch
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable


class ScanIntent(Enum):
    """扫描意图枚举"""
    DEFAULT = "default"           # 默认扫描，仅排除明显无关文件
    STRICT = "strict"            # 严格扫描，排除所有非源码文件
    PERFORMANCE = "performance"  # 性能优化扫描，排除大文件和测试文件
    SECURITY = "security"        # 安全扫描，关注敏感文件和权限
    CLEANUP = "cleanup"          # 清理扫描，识别可删除的临时文件


@dataclass
class ScanPattern:
    """扫描模式配置"""
    name: str
    description: str
    include_patterns: List[str]   # 包含模式
    exclude_patterns: List[str]   # 排除模式
    max_file_size: Optional[int] = None  # 最大文件大小（字节）
    check_function: Optional[Callable[[Path], bool]] = None  # 自定义检查函数


class SmartScannerOptimizer:
    """智能扫描优化器"""

    # 默认排除模式（适用于所有意图）
    DEFAULT_EXCLUDE_PATTERNS = [
        # 版本控制目录
        ".git", ".svn", ".hg",
        # IDE和编辑器文件
        ".idea", ".vscode", ".vs", ".settings",
        # 构建产物
        "__pycache__", "*.pyc", "*.pyo", "*.pyd",
        "*.so", "*.dll", "*.dylib",
        # 包管理
        "*.egg", "*.egg-info", "dist", "build",
        "pip-wheel-metadata", ".pytest_cache",
        # 虚拟环境
        "venv", "env", ".env", ".venv",
        # 日志和缓存
        "*.log", "*.tmp", "*.temp", ".cache",
        # 系统文件
        ".DS_Store", "Thumbs.db",
        # 配置文件（可能包含敏感信息）
        ".env.local", ".env.*.local",
    ]

    # 意图特定的模式配置
    INTENT_PATTERNS = {
        ScanIntent.DEFAULT: ScanPattern(
            name="default",
            description="默认扫描模式，平衡速度和完整性",
            include_patterns=["*.py"],
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
            max_file_size=10 * 1024 * 1024,  # 10MB
        ),
        ScanIntent.STRICT: ScanPattern(
            name="strict",
            description="严格扫描模式，仅扫描源码文件",
            include_patterns=["*.py"],
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS + [
                "test_*.py", "*_test.py",  # 测试文件
                "setup.py", "setup.cfg",   # 构建配置
                "requirements*.txt",       # 依赖文件
                "*.md", "*.rst", "*.txt",  # 文档文件
            ],
            max_file_size=5 * 1024 * 1024,  # 5MB
        ),
        ScanIntent.PERFORMANCE: ScanPattern(
            name="performance",
            description="性能优化扫描，排除大文件和测试文件",
            include_patterns=["*.py"],
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS + [
                "test_*.py", "*_test.py", "tests/",
                "*.pyc", "*.pyo",  # 字节码文件
                "*.log", "*.cache",  # 日志和缓存
            ],
            max_file_size=2 * 1024 * 1024,  # 2MB
            check_function=lambda p: p.stat().st_size < 2 * 1024 * 1024,
        ),
        ScanIntent.SECURITY: ScanPattern(
            name="security",
            description="安全扫描，关注敏感文件和权限",
            include_patterns=["*.py", "*.yaml", "*.yml", "*.json", "*.env", "*.cfg"],
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
            check_function=lambda p: SmartScannerOptimizer._check_file_security(p),
        ),
        ScanIntent.CLEANUP: ScanPattern(
            name="cleanup",
            description="清理扫描，识别可删除的临时文件",
            include_patterns=["*"],
            exclude_patterns=[],
            check_function=lambda p: SmartScannerOptimizer._is_temp_file(p),
        ),
    }

    def __init__(self, console, intent: ScanIntent = ScanIntent.DEFAULT):
        """
        初始化优化器

        Args:
            console: Rich Console 实例
            intent: 扫描意图
        """
        self.console = console
        self.intent = intent
        self.pattern = self.INTENT_PATTERNS.get(intent, self.INTENT_PATTERNS[ScanIntent.DEFAULT])

    def filter_files(self, directory: Path, recursive: bool = True) -> List[Path]:
        """
        智能过滤文件

        Args:
            directory: 要扫描的目录
            recursive: 是否递归扫描

        Returns:
            过滤后的文件列表
        """
        if not directory.exists():
            return []

        all_files = []
        if recursive:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    all_files.append(file_path)
        else:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    all_files.append(file_path)

        filtered_files = []
        excluded_count = 0
        excluded_by_pattern = {}

        for file_path in all_files:
            # 检查是否应该排除
            should_exclude, reason = self._should_exclude_file(file_path)

            if should_exclude:
                excluded_count += 1
                if reason not in excluded_by_pattern:
                    excluded_by_pattern[reason] = 0
                excluded_by_pattern[reason] += 1
                continue

            # 检查是否应该包含（基于include_patterns）
            if not self._should_include_file(file_path):
                excluded_count += 1
                excluded_by_pattern["not_in_include_patterns"] = excluded_by_pattern.get("not_in_include_patterns", 0) + 1
                continue

            # 检查文件大小限制
            if self.pattern.max_file_size:
                try:
                    file_size = file_path.stat().st_size
                    if file_size > self.pattern.max_file_size:
                        excluded_count += 1
                        excluded_by_pattern["file_too_large"] = excluded_by_pattern.get("file_too_large", 0) + 1
                        continue
                except (OSError, IOError):
                    continue

            # 执行自定义检查函数
            if self.pattern.check_function and not self.pattern.check_function(file_path):
                excluded_count += 1
                excluded_by_pattern["custom_check_failed"] = excluded_by_pattern.get("custom_check_failed", 0) + 1
                continue

            filtered_files.append(file_path)

        # 输出过滤统计信息
        self._print_filter_stats(len(all_files), len(filtered_files), excluded_count, excluded_by_pattern)

        return filtered_files

    def _should_exclude_file(self, file_path: Path) -> tuple[bool, str]:
        """
        检查文件是否应该被排除

        Returns:
            (should_exclude, reason)
        """
        # 检查排除模式
        for pattern in self.pattern.exclude_patterns:
            # 处理目录模式
            if pattern.endswith('/') or '/' in pattern:
                dir_pattern = pattern.rstrip('/')
                if fnmatch.fnmatch(str(file_path.parent), f"*/{dir_pattern}") or \
                   fnmatch.fnmatch(str(file_path.parent), dir_pattern):
                    return True, f"directory_pattern:{pattern}"

            # 处理文件模式
            if fnmatch.fnmatch(file_path.name, pattern):
                return True, f"file_pattern:{pattern}"

            # 处理路径模式
            if fnmatch.fnmatch(str(file_path), f"*/{pattern}"):
                return True, f"path_pattern:{pattern}"

        return False, ""

    def _should_include_file(self, file_path: Path) -> bool:
        """
        检查文件是否应该被包含
        """
        if not self.pattern.include_patterns:
            return True

        for pattern in self.pattern.include_patterns:
            if fnmatch.fnmatch(file_path.name, pattern):
                return True

        return False

    def _print_filter_stats(self, total: int, filtered: int, excluded: int, excluded_by_pattern: Dict[str, int]):
        """输出过滤统计信息"""
        if total == 0:
            return

        self.console.print(f"[bold cyan]📊 扫描优化统计:[/bold cyan]")
        self.console.print(f"  扫描模式: [yellow]{self.pattern.name}[/yellow] ({self.pattern.description})")
        self.console.print(f"  总文件数: {total}")
        self.console.print(f"  过滤后: {filtered}")
        self.console.print(f"  排除数: {excluded} ({excluded/total*100:.1f}%)")

        if excluded_by_pattern:
            self.console.print(f"  [dim]排除原因分布:[/dim]")
            for reason, count in sorted(excluded_by_pattern.items(), key=lambda x: x[1], reverse=True):
                percentage = count / excluded * 100 if excluded > 0 else 0
                reason_display = reason.replace("_", " ").title()
                self.console.print(f"    • {reason_display}: {count} ({percentage:.1f}%)")

    @staticmethod
    def _check_file_security(file_path: Path) -> bool:
        """检查文件安全性"""
        # 检查文件权限（仅限Unix-like系统）
        try:
            import os
            import stat
            mode = file_path.stat().st_mode
            # 检查是否有过于宽松的权限
            if mode & stat.S_IWOTH:  # 其他用户可写
                return False
            if mode & stat.S_IROTH and file_path.name.endswith(('.env', '.cfg', '.yaml', '.yml')):
                return False  # 敏感配置文件不应全局可读
        except (AttributeError, ImportError):
            pass

        # 检查文件名是否包含敏感关键词
        sensitive_keywords = ['secret', 'password', 'token', 'key', 'credential']
        file_name_lower = file_path.name.lower()
        for keyword in sensitive_keywords:
            if keyword in file_name_lower:
                return False

        return True

    @staticmethod
    def _is_temp_file(file_path: Path) -> bool:
        """检查是否为临时文件"""
        temp_patterns = [
            '*.tmp', '*.temp', '*.bak', '*.backup',
            '*.swp', '*.swo', '~*', '#*#',
            '*.log', '*.cache', '*.pid',
        ]

        for pattern in temp_patterns:
            if fnmatch.fnmatch(file_path.name, pattern):
                return True

        # 检查文件名是否包含临时标记
        temp_keywords = ['temp', 'tmp', 'backup', 'old', 'new']
        file_stem = file_path.stem.lower()
        for keyword in temp_keywords:
            if keyword in file_stem:
                return True

        return False

    def analyze_code_quality(self, file_path: Path) -> Dict[str, Any]:
        """
        分析代码质量

        Returns:
            质量分析结果
        """
        analysis = {
            "file": str(file_path),
            "issues": [],
            "suggestions": [],
            "score": 100,  # 初始分数
        }

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # 检查文件编码
            if 'coding:' not in content[:100] and 'utf-8' not in content[:100].lower():
                analysis["issues"].append("缺少明确的UTF-8编码声明")
                analysis["score"] -= 5

            # 检查行长度
            lines = content.split('\n')
            long_lines = [i+1 for i, line in enumerate(lines) if len(line.rstrip()) > 120]
            if long_lines:
                analysis["issues"].append(f"第 {', '.join(map(str, long_lines[:5]))} 行超过120字符")
                analysis["score"] -= len(long_lines) * 2

            # 检查TODO/FIXME注释
            todo_pattern = re.compile(r'#\s*(TODO|FIXME|XXX|HACK):?\s*(.+)', re.IGNORECASE)
            todos = list(todo_pattern.finditer(content))
            if todos:
                analysis["issues"].append(f"发现 {len(todos)} 个TODO/FIXME注释")
                analysis["suggestions"].append("请及时处理TODO/FIXME注释")
                analysis["score"] -= len(todos) * 3

            # 检查导入顺序（简单检查）
            import_lines = [i+1 for i, line in enumerate(lines) if line.strip().startswith('import ') or line.strip().startswith('from ')]
            if len(import_lines) > 1:
                # 检查导入是否分组
                groups = 0
                prev_line = -10
                for line_num in import_lines:
                    if line_num - prev_line > 2:
                        groups += 1
                    prev_line = line_num

                if groups > 3:  # 太多分散的导入
                    analysis["suggestions"].append("建议将import语句分组整理")
                    analysis["score"] -= 5

        except Exception as e:
            analysis["issues"].append(f"读取文件失败: {str(e)}")
            analysis["score"] = 0

        return analysis

    def get_optimization_suggestions(self, directory: Path) -> List[str]:
        """
        获取优化建议

        Args:
            directory: 要分析的目录

        Returns:
            优化建议列表
        """
        suggestions = []

        # 检查目录结构
        if not (directory / "tools").exists():
            suggestions.append("缺少 'tools/' 目录，这是DefineX插件必需的目录结构")

        # 检查是否有不必要的文件
        all_files = list(directory.rglob("*"))
        temp_files = [f for f in all_files if f.is_file() and self._is_temp_file(f)]
        if temp_files:
            suggestions.append(f"发现 {len(temp_files)} 个临时文件，建议清理")

        # 检查文件大小
        large_files = []
        for file_path in all_files:
            if file_path.is_file():
                try:
                    if file_path.stat().st_size > 5 * 1024 * 1024:  # 5MB
                        large_files.append(file_path)
                except (OSError, IOError):
                    pass

        if large_files:
            suggestions.append(f"发现 {len(large_files)} 个大文件(>5MB)，考虑优化或排除")

        return suggestions


def create_scanner_with_intent(console, intent: str = "default") -> SmartScannerOptimizer:
    """
    创建指定意图的扫描优化器

    Args:
        console: Rich Console 实例
        intent: 意图字符串，可选值: default, strict, performance, security, cleanup

    Returns:
        SmartScannerOptimizer 实例
    """
    intent_map = {
        "default": ScanIntent.DEFAULT,
        "strict": ScanIntent.STRICT,
        "performance": ScanIntent.PERFORMANCE,
        "security": ScanIntent.SECURITY,
        "cleanup": ScanIntent.CLEANUP,
    }

    selected_intent = intent_map.get(intent.lower(), ScanIntent.DEFAULT)
    return SmartScannerOptimizer(console, selected_intent)
