import argparse
import sys

from rich.console import Console

from definex.plugin.manager import PluginManager

console = Console()

def main():
    # 1. 创建主解析器
    parser = argparse.ArgumentParser(
        prog="dfx",
        description="DefineX (dfx) - 工业级插件开发、编排与 AI 协议转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  dfx plugin init my_plugin             # 初始化新插件
  dfx plugin watch                      # 开启自动化监听哨兵
  dfx plugin run native --repl          # 进入交互式测试终端
  dfx plugin run mcp --protocol sse     # 启动远程 AI 协议服务
  dfx plugin build                      # 构建并打包依赖隔离环境
        """
    )

    # 2. 定义顶级命令组
    subparsers = parser.add_subparsers(dest="group", title="命令分组", metavar="<group>")

    # --- [Plugin 组] ---
    plugin_parser = subparsers.add_parser("plugin", help="插件开发全生命周期管理")
    plugin_sub = plugin_parser.add_subparsers(dest="command", title="插件子命令", metavar="<command>")

    # dfx plugin init
    init_p = plugin_sub.add_parser("init", help="初始化插件项目 (含虚拟环境构建)")
    init_p.add_argument("name", help="项目文件夹名称")

    # dfx plugin manifest
    mani_p = plugin_sub.add_parser("manifest", help="提取 tools/ 代码生成契约文件 (manifest.yaml)")
    mani_p.add_argument("path", nargs="?", default=".", help="项目根目录")
    mani_p.add_argument("--intent", choices=["default", "strict", "performance", "security", "cleanup"],
                       default="default", help="扫描意图模式 (默认: default)")

    # dfx plugin analyze
    analyze_p = plugin_sub.add_parser("analyze", help="分析代码质量并提供优化建议")
    analyze_p.add_argument("path", nargs="?", default=".", help="项目根目录")
    analyze_p.add_argument("--intent", choices=["default", "strict", "performance", "security", "cleanup"],
                          default="strict", help="分析意图模式 (默认: strict)")

    # dfx plugin guide
    guide_p = plugin_sub.add_parser("guide", help="进入交互式菜单操作界面")
    guide_p.add_argument("path", nargs="?", default=".", help="项目根目录")

    # dfx plugin check
    check_p = plugin_sub.add_parser("check", help="深度合规性检查 (比对源码、校验描述、检查黑盒)")
    check_p.add_argument("path", nargs="?", default=".", help="项目根目录")

    # dfx plugin watch
    watch_p = plugin_sub.add_parser("watch", help="[开发利器] 监听 tools/ 变动，自动执行 manifest 与 check")
    watch_p.add_argument("path", nargs="?", default=".", help="项目根目录")

    # dfx plugin build
    build_p = plugin_sub.add_parser("build", help="构建隔离运行环境并打包为 .dfxpkg 文件")
    build_p.add_argument("path", nargs="?", default=".", help="项目根目录")

    # --- [Plugin Run 组] ---
    run_parser = plugin_sub.add_parser("run", help="插件运行与调试中心")
    run_mode_sub = run_parser.add_subparsers(dest="mode", title="运行模式", metavar="<mode>", required=True)

    # dfx plugin run native
    native_p = run_mode_sub.add_parser("native", help="原生测试模式 (本地逻辑验证)")
    native_p.add_argument("path", nargs="?", default=".", help="插件路径")
    # Native 细分模式参数
    n_group = native_p.add_argument_group("模式与参数")
    n_group.add_argument("--action", help="[单次执行] 指定要运行的 Action 名称")
    n_group.add_argument("--params", help="[单次执行] JSON 格式参数字符串")
    n_group.add_argument("--repl", action="store_true", help="[人类交互] 启动交互式命令行")
    n_group.add_argument("--debug", action="store_true", help="[程序交互] 启动标准 JSON 流接口 (IPC)")
    native_p.add_argument("--watch", action="store_true", help="启用代码热重载")

    # dfx plugin run mcp
    mcp_p = run_mode_sub.add_parser("mcp", help="AI 协议模式 (对接 Model Context Protocol)")
    mcp_p.add_argument("path", nargs="?", default=".", help="插件路径")
    mcp_p.add_argument("--protocol", choices=["stdio", "http", "sse"], default="stdio", help="传输协议 (默认: stdio)")
    mcp_p.add_argument("--port", type=int, default=8080, help="服务端口 (仅 http/sse 模式有效)")
    mcp_p.add_argument("--watch", action="store_true", help="代码变动时自动更新契约元数据")

    # --- [plugin config] ---
    config_parser = plugin_sub.add_parser("config", help="管理全局配置")
    config_sub = config_parser.add_subparsers(dest="config_type", required=True)

    # dfx plugin config llm
    llm_p = config_sub.add_parser("llm", help="配置大模型信息")
    llm_p.add_argument("--api-key", help="API Key")
    llm_p.add_argument("--model", help="模型名称 (如 gpt-4o)")
    llm_p.add_argument("--url", help="Base URL / Proxy URL")

    # --- [plugin config push] ---
    push_cfg_p = config_sub.add_parser("push", help="配置发布环境")
    push_cfg_p.add_argument("env", help="环境名称 (如 dev, prod)")
    push_cfg_p.add_argument("--url", help="服务器上传地址")
    push_cfg_p.add_argument("--token", help="认证 Token")

    # dfx plugin push
    push_p = plugin_sub.add_parser("push", help="发布插件到指定环境")
    push_p.add_argument("path", nargs="?", default=".", help="路径")
    push_p.add_argument("-e", "--env", help="指定目标环境 (默认使用 config 中的 default)")
    push_p.add_argument("--url", help="手动指定 URL (覆盖配置)")
    push_p.add_argument("--token", help="手动指定 Token (覆盖配置)")

    # --- [plugin code] ---
    code_p = plugin_sub.add_parser("code", help="启动 AI 辅助编码")
    code_p.add_argument("path", nargs="?", default=".", help="路径")
    code_p.add_argument("--chat", action="store_true", help="普通对话模式 (不强制生成代码)")

    # --- [plugin remote debugger] ---
    debug_p = plugin_sub.add_parser("debug", help="启动远程调试模式 (实时连接云端工作流)")
    debug_p.add_argument("path", nargs="?", default=".", help="路径")
    debug_p.add_argument("-e", "--env", help="指定调试环境 (dev/prod)")
    debug_p.add_argument("--protocol", choices=["ws", "sse"], default="ws", help="通信协议 (默认: ws)")

    # 3. 参数解析与逻辑调度
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # 特殊处理：支持 dfx plugin run native --action say_hello path '{"name": "value"}' 格式
    # 检查是否有类似 JSON 的参数
    import json
    args_to_parse = sys.argv[1:]
    params_json = None

    # 查找可能的 JSON 参数（从倒数第一个参数开始检查）
    for i in range(len(args_to_parse) - 1, -1, -1):
        arg = args_to_parse[i]
        # 检查是否是 JSON 对象
        if arg.startswith('{') and arg.endswith('}'):
            try:
                # 尝试解析 JSON
                json.loads(arg)
                # 如果是有效的 JSON，将其作为 params_json
                params_json = arg
                # 从参数列表中移除
                args_to_parse = args_to_parse[:i] + args_to_parse[i+1:]
                break
            except json.JSONDecodeError:
                # 不是有效的 JSON，继续检查
                pass

    # 使用修改后的参数列表进行解析
    args = parser.parse_args(args_to_parse)

    # 如果检测到 JSON 参数，将其添加到 args 中
    if params_json and hasattr(args, 'params') and args.params is None:
        args.params = params_json

    mgr = PluginManager()

    try:
        if args.group == "plugin":
            # 生命周期命令处理
            if args.command == "init":
                mgr.init(args.name)
            elif args.command == "guide":
                mgr.guide_menu(args.path)
            elif args.command == "manifest":
                mgr.manifest(args.path, intent=args.intent)
            elif args.command == "analyze":
                mgr.analyze(args.path, intent=args.intent)
            elif args.command == "check":
                mgr.check(args.path)
            elif args.command == "watch":
                mgr.watch(args.path)
            elif args.command == "build":
                mgr.build(args.path)
            elif args.command == "push":
                mgr.push(args.path, env=args.env, url=args.url, token=args.token)
            elif args.command == "config":
                # 统一传递所有可能的参数，由config方法根据section决定使用哪些
                mgr.config(
                    section=args.config_type,
                    env=getattr(args, 'env', None),
                    api_key=getattr(args, 'api_key', None),
                    model=getattr(args, 'model', None),
                    base_url=getattr(args, 'url', None),  # 注意：cli中的--url对应base_url
                    url=getattr(args, 'url', None),  # push配置中的url
                    token=getattr(args, 'token', None)
                )
            elif args.command == "code":
                mgr.code(args.path, mode="chat" if args.chat else "code")
            # 运行命令处理
            elif args.command == "run":
                if args.mode == "native":
                    mgr.run(
                        path=args.path, mode="native", action=args.action,
                        params_json=args.params, repl=args.repl,
                        debug=args.debug, watch=args.watch
                    )
                elif args.mode == "mcp":
                    mgr.run(
                        path=args.path, mode="mcp",
                        protocol=args.protocol, port=args.port, watch=args.watch
                    )
            elif args.command == "debug":
                mgr.debug(args.path, env=args.env, protocol=args.protocol)
            else:
                plugin_parser.print_help()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 操作已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ 执行过程中发生异常:[/bold red] {e}")
        # 如果需要查看底层堆栈，可以在环境变量中开启 DEBUG 模式
        # import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()
