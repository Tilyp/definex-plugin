import functools
import sys
from pathlib import Path

from rich.console import Console

console = Console()

def ensure_project(func):
    """
    装饰器：DefineX 项目环境守门员

    校验逻辑：
    1. 获取方法传入的 path 参数。
    2. 如果路径是 .dfxpkg 或 .pkg 文件，视为运行成品，准许通过。
    3. 如果是目录，则该目录下必须存在 manifest.yaml，否则强制退出。
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # 1. 尝试定位路径参数 (位置参数优先，其次关键字参数，默认当前目录)
        path_arg = args[0] if args else kwargs.get('path', '.')
        target_path = Path(path_arg).resolve()

        # 2. 特例处理：如果正在运行或推送一个现成的包文件，跳过项目结构检查
        if target_path.is_file() and target_path.suffix in ['.pkg', '.dfxpkg']:
            return func(self, *args, **kwargs)

        # 3. 确定校验目录 (如果是目录则检查自身，如果是文件则检查其父目录)
        check_dir = target_path if target_path.is_dir() else target_path.parent
        marker = check_dir / "manifest.yaml"

        # 4. 执行物理存在性检查
        if not marker.exists():
            console.print(f"\n[bold red]❌ 操作被拦截: 环境校验失败[/bold red]")
            console.print(f"[yellow]原因:[/yellow] 路径 [cyan]{check_dir}[/cyan] 下未发现 [bold]manifest.yaml[/bold]")
            console.print(f"[dim]提示: 请确认是否在项目根目录下运行，或先执行 'dfx plugin init'。[/dim]\n")
            # 强行终止后续所有逻辑
            sys.exit(1)

        # 5. 校验通过，透传调用
        return func(self, *args, **kwargs)

    return wrapper
