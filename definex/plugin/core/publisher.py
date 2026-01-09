import sys

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn


class PluginPublisher:
    def __init__(self, console: Console, config_mgr, env_name: str = None,
                 cmd_url: str = None, cmd_token: str = None):
        self.console = console

        # 1. 解析配置
        push_config = config_mgr.get_section("push")
        envs = push_config.get("environments", {})

        # 2. 决议目标环境 (优先级: 命令行 -e > 默认环境)
        self.target_env = env_name or push_config.get("default")
        env_settings = envs.get(self.target_env, {}) if self.target_env else {}

        # 3. 决议最终参数 (优先级: 命令行覆盖 > 环境配置)
        self.final_url = cmd_url or env_settings.get("url")
        self.final_token = cmd_token or env_settings.get("token")

        # 4. 强制合法性校验 (初始化即判断)
        if not self.final_url:
            self.console.print(f"\n[bold red]❌ 发布终止: 未指定目标 URL。[/bold red]")
            self.console.print(f"[yellow]请先配置环境或使用 --url 参数。[/yellow]")
            self.console.print(f"[dim]示例: dfx plugin config push dev --url http://...[/dim]\n")
            sys.exit(1)

        if not self.final_token:
            self.console.print(f"\n[bold red]❌ 发布终止: 缺失认证 Token。[/bold red]")
            sys.exit(1)

    def publish(self, pkg_path: str):
        """执行物理上传流程"""
        self.console.print(f"\n🚀 [bold blue]目标环境:[/bold blue] [green]{self.target_env}[/green]")
        self.console.print(f"📡 [bold blue]上传地址:[/bold blue] [cyan]{self.final_url}[/cyan]\n")

        try:
            file_size = pkg_path.stat().st_size
            with open(pkg_path, "rb") as f:
                files = {"file": (pkg_path.name, f, "application/octet-stream")}
                headers = {"Authorization": f"Bearer {self.final_token}"}

                with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        DownloadColumn(),
                        console=self.console,
                        transient=True
                ) as progress:
                    task = progress.add_task(f"正在传输 {pkg_path.name}...", total=file_size)
                    response = requests.post(self.final_url, files=files, headers=headers, timeout=120)
                    progress.update(task, completed=file_size)

            if response.status_code == 200:
                self.console.print(f"[bold green]✅ 插件包推送成功！[/bold green]")
                return True
            else:
                self.console.print(f"[bold red]❌ 服务端报错 ({response.status_code}):[/bold red] {response.text}")
                return False
        except Exception as e:
            self.console.print(f"[bold red]❌ 网络通信异常:[/bold red] {e}")
            return False