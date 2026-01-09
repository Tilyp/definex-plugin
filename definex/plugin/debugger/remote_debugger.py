import json
import asyncio

import httpx
import websockets
import yaml
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from definex.plugin.runtime import PluginRuntime

class PluginRemoteDebugger:
    """
    REGISTER: POST /debug/register (SSE 模式需要)
    WS 通道: ws://.../debug/ws
    SSE 通道: get://.../debug/sse
    结果回传: POST /debug/result (SSE 模式专用)
    """

    def __init__(self, console: Console, generator):
        self.console = console
        self.generator = generator

    def _get_ws_url(self, http_url: str):
        return http_url.replace("http", "ws").replace("/upload", "/debug")

    def connect(self, root_path: Path, url: str, token: str, env_label: str, protocol: str):
        """建立连接入口"""
        # 0. 准备 Manifest
        self.generator.generate(root_path)
        with open(root_path / "manifest.yaml", "r") as f:
            manifest = yaml.safe_load(f)

        self.console.print(Panel(
            f"🚀 [bold green]DefineX 远程调试准备中[/bold green]\n"
            f"🌍 环境: {env_label} | 协议: {protocol.upper()}",
            border_style="cyan"
        ))

        if protocol == "ws":
            asyncio.run(self._run_ws(root_path, url, token, manifest))
        else:
            asyncio.run(self._run_sse(root_path, url, token, manifest))


    # --- WebSocket 实现 ---
    async def _run_ws(self, root_path, http_url, token, manifest):
        ws_url = http_url.replace("http", "ws").replace("/upload", "/debug/ws")
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                # 注册
                await ws.send(json.dumps({
                    "type": "REGISTER_DEBUGGER",
                    "plugin_id": manifest["plugin_info"]["id"],
                    "manifest": manifest
                }))
                self.console.print(f"[green]📡 WebSocket 隧道已建立: {ws_url}[/green]")

                async for message in ws:
                    data = json.loads(message)
                    if data.get("type") == "INVOKE":
                        result = self._handle_invoke(root_path, data)
                        await ws.send(json.dumps({
                            "type": "RESULT",
                            "request_id": data["request_id"],
                            **result
                        }))
        except Exception as e:
            self.console.print(f"[bold red]❌ WS 连接中断:[/bold red] {e}")

    # --- SSE 实现 ---
    async def _run_sse(self, root_path, http_url, token, manifest):
        sse_url = http_url.replace("/upload", "/debug/sse")
        result_url = http_url.replace("/upload", "/debug/result")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. 首先通过 POST 注册自己
        async with httpx.AsyncClient() as client:
            reg_resp = await client.post(
                http_url.replace("/upload", "/debug/register"),
                json={"plugin_id": manifest["plugin_info"]["id"], "manifest": manifest},
                headers=headers
            )
            if reg_resp.status_code != 200:
                self.console.print(f"[red]❌ SSE 注册失败: {reg_resp.text}[/red]")
                return

        self.console.print(f"[green]📡 SSE 监听流已开启: {sse_url}[/green]")

        # 2. 开始监听 SSE 事件流
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", sse_url, headers=headers) as response:
                    async for line in response.iter_lines():
                        if line.startswith("data:"):
                            data = json.loads(line[5:])
                            if data.get("type") == "INVOKE":
                                result = self._handle_invoke(root_path, data)
                                # SSE 必须通过独立的 POST 回传结果
                                await client.post(result_url, json={
                                    "request_id": data["request_id"],
                                    **result
                                }, headers=headers)
                                self.console.print("[dim]📤 结果已通过 HTTP POST 回传[/dim]")
        except Exception as e:
            self.console.print(f"[bold red]❌ SSE 连接异常:[/bold red] {e}")


    async def _handle_invoke(self, req, root_path: Path):
        """执行本地代码并返回"""
        action, params = req["action"], req["params"]
        self.console.print(f"📥 [bold cyan]收到云端调用:[/bold cyan] {action}")
        try:
            # 实例化运行时执行本地代码
            rt = PluginRuntime(root_path)
            result = rt.execute(action, params)
            resp = {"status": "success", "payload": result}
            self.console.print(f"📤 [bold green]执行成功，结果已回传[/bold green]")
        except Exception as e:
            self.console.print(f"❌ [bold red]执行失败:[/bold red] {e}")
            resp = {"status": "error", "message": str(e)}
        return resp