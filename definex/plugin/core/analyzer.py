"""
DefineX 代码分析器 - 专门处理代码分析业务逻辑
从 PluginManager 中提取的业务逻辑
"""

from pathlib import Path
from typing import Dict, Any

from rich.console import Console

from definex.plugin.core.annotation_validator import validate_actions
from definex.plugin.core.optimizer import create_scanner_with_intent
from definex.plugin.core.scanner import CodeScanner


class CodeAnalyzer:
    """代码分析器 - 专门处理代码质量分析业务逻辑"""

    def __init__(self, console: Console, scanner: CodeScanner):
        """
        初始化分析器

        Args:
            console: 控制台输出
            scanner: 代码扫描器
        """
        self.console = console
        self.scanner = scanner

    def analyze_code_quality(self, path: str, intent: str = "strict") -> Dict[str, Any]:
        """
        分析代码质量和提供优化建议

        Args:
            path: 插件路径
            intent: 分析意图，可选值: default, strict, performance, security, cleanup

        Returns:
            分析报告
        """
        root = Path(path).resolve()

        self.console.print(f"[bold cyan]📊 开始代码质量分析 (模式: {intent})...[/bold cyan]")

        # 使用智能扫描优化器
        optimizer = create_scanner_with_intent(self.console, intent)

        # 1. 获取优化建议
        suggestions = optimizer.get_optimization_suggestions(root)
        if suggestions:
            self.console.print("[bold yellow]💡 项目优化建议:[/bold yellow]")
            for i, suggestion in enumerate(suggestions, 1):
                self.console.print(f"  {i}. {suggestion}")

        # 2. 分析代码质量
        analysis_report = self.scanner.analyze_code_quality(root)

        if "error" in analysis_report:
            self.console.print(f"[red]❌ 分析失败: {analysis_report['error']}[/red]")
            return analysis_report

        # 3. 检查参数注解是否符合规范（使用统一工具）
        self._check_parameter_annotations(root)

        self._print_analysis_summary(analysis_report)
        self._print_detailed_issues(analysis_report)
        self._print_scan_mode_suggestions(analysis_report)

        return analysis_report

    def _check_parameter_annotations(self, root: Path) -> None:
        """
        检查参数注解是否符合规范（使用统一工具）

        Args:
            root: 插件项目根目录
        """
        self.console.print("\n[bold blue]🔍 正在检查参数注解规范...[/bold blue]")

        # 使用扫描器获取所有 Action
        actions = self.scanner.scan_tools_directory(root)

        # 使用统一工具校验
        errors = validate_actions(actions)

        if errors:
            self.console.print("[bold red]❌ 发现参数注解问题:[/bold red]")
            for error in errors:
                self.console.print(f"  [red]✗ {error}[/red]")
            self.console.print("\n[bold yellow]💡 修正建议:[/bold yellow]")
            self.console.print("    1. 所有参数必须使用 Annotated[类型, \"描述\"] 格式")
            self.console.print("    2. Annotated 注解必须包含描述信息")
            self.console.print("    3. 示例: Annotated[str, \"用户名\"]")
        else:
            self.console.print("[green]✅ 所有参数注解符合规范[/green]")

    def _print_analysis_summary(self, analysis_report: Dict[str, Any]) -> None:
        """打印分析摘要"""
        self.console.print(f"\n[bold cyan]📈 代码质量报告:[/bold cyan]")
        self.console.print(f"  分析文件数: {analysis_report['files_analyzed']}/{analysis_report['total_files']}")
        self.console.print(f"  发现问题数: {analysis_report['issues_found']}")
        self.console.print(f"  质量评分: {analysis_report['average_score']:.1f}/100")

        if analysis_report['suggestions']:
            self.console.print(f"\n[bold yellow]🔧 代码改进建议:[/bold yellow]")
            for i, suggestion in enumerate(analysis_report['suggestions'], 1):
                self.console.print(f"  {i}. {suggestion}")

    def _print_detailed_issues(self, analysis_report: Dict[str, Any]) -> None:
        """打印详细问题"""
        if analysis_report['issues_found'] > 0:
            self.console.print(f"\n[bold red]⚠️ 发现的问题详情:[/bold red]")
            for file_detail in analysis_report['file_details']:
                if file_detail.get('issues'):
                    self.console.print(f"  📄 {file_detail['file']} (评分: {file_detail['score']}/100)")
                    for issue in file_detail['issues'][:3]:  # 只显示前3个问题
                        self.console.print(f"    • {issue}")
                    if len(file_detail['issues']) > 3:
                        self.console.print(f"    ... 还有 {len(file_detail['issues']) - 3} 个问题")

    def _print_scan_mode_suggestions(self, analysis_report: Dict[str, Any]) -> None:
        """根据分析结果提供扫描模式建议"""
        suggestions = []

        if analysis_report['issues_found'] > 10:
            suggestions.append("发现较多问题，建议使用 'strict' 模式进行严格扫描")

        if analysis_report['average_score'] < 70:
            suggestions.append("代码质量较低，建议使用 'performance' 模式优化")

        if analysis_report['total_files'] - analysis_report['files_analyzed'] > 5:
            suggestions.append("有较多文件被排除，建议使用 'cleanup' 模式清理不必要的文件")

        if suggestions:
            self.console.print(f"\n[bold green]🚀 扫描模式建议:[/bold green]")
            for suggestion in suggestions:
                self.console.print(f"  • {suggestion}")

        self.console.print(f"\n[dim]💡 提示: 使用 dfx plugin manifest --intent <mode> 指定扫描模式[/dim]")
        self.console.print(f"[dim]      可选模式: default, strict, performance, security, cleanup[/dim]")

    def get_quick_analysis(self, path: str) -> Dict[str, Any]:
        """
        快速分析代码

        Args:
            path: 插件路径

        Returns:
            简化版分析报告
        """
        root = Path(path).resolve()
        report = self.scanner.analyze_code_quality(root)

        # 提取关键信息
        return {
            'files_analyzed': report.get('files_analyzed', 0),
            'total_files': report.get('total_files', 0),
            'issues_found': report.get('issues_found', 0),
            'average_score': report.get('average_score', 0),
            'status': 'error' if 'error' in report else 'success'
        }

    def compare_analysis(self, path1: str, path2: str) -> Dict[str, Any]:
        """
        比较两个项目的代码质量

        Args:
            path1: 第一个项目路径
            path2: 第二个项目路径

        Returns:
            比较报告
        """
        report1 = self.get_quick_analysis(path1)
        report2 = self.get_quick_analysis(path2)

        return {
            'project1': report1,
            'project2': report2,
            'comparison': {
                'score_difference': report1['average_score'] - report2['average_score'],
                'issues_difference': report1['issues_found'] - report2['issues_found'],
                'better_project': 'project1' if report1['average_score'] > report2['average_score'] else 'project2'
            }
        }


# ==================== 工厂函数 ====================

def create_code_analyzer(console: Console, scanner: CodeScanner) -> CodeAnalyzer:
    """创建代码分析器实例"""
    return CodeAnalyzer(console, scanner)
