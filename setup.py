from setuptools import setup, find_packages

# 读取 README 作为长描述
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="definex",
    version="0.1.0",
    author="DefineX Team",
    description="插件开发与编排脚手架工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,  # 极其重要：结合 MANIFEST.in 包含非 .py 文件
    python_requires=">=3.9",
    install_requires=[
        # 基础框架
        "PyYAML>=6.0.1",
        "rich>=13.7.1",
        "click>=8.1.8",

        # MCP 协议支持
        "mcp>=1.0.0",
        "fastmcp>=2.14.1",

        # Web 服务
        "uvicorn>=0.30.1",
        "starlette>=0.47.2",
        "sse-starlette>=2.2.1",

        # 安全
        "cryptography>=42.0.0",

        # 文件监控
        "watchdog>=4.0.0",

        # 网络请求
        "requests>=2.32.4",

        # 类型支持
        "typing-extensions>=4.0.0",

        # 终端优化 (新增)
        "prompt-toolkit>=3.0.0",  # 更好的终端输入体验

        # openai
        "openai>=1.61.1",
        
        # 调试支持
        "httpx>=0.27.0",
        "websockets>=12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.4.2",
            "pytest-cov>=5.0.0",
            "pytest-asyncio>=0.23.0",
            "mypy>=1.11.2",
            "black>=24.0.0",
            "isort>=5.13.0",
            "flake8>=7.0.0",
            "types-PyYAML>=6.0.12",
            "types-requests>=2.31.0",
        ],
        "full": [
            "sqlalchemy>=1.4.54",
            "redis>=5.2.1",
            "pillow>=10.4.0",
            "orjson>=3.10.16",
            "pydantic>=2.11.9",
            "jsonschema>=4.23.0",
        ]
    },
    entry_points={
        "console_scripts": [
            # 核心：将 dfx 命令映射到 definex/plugin/cli.py 中的 main 函数
            "dfx=definex.plugin.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Build Tools",
    ],
)
