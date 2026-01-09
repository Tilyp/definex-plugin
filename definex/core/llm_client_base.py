"""
统一的LLM客户端基础类
提供核心的LLM客户端管理功能，可被其他模块继承和扩展
"""

import time
from typing import Dict, List, Optional, Any

from openai import OpenAI, AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from .config_models import ModelProvider, LLMModelConfig


class LLMClientBase:
    """LLM客户端基础类 - 提供核心功能"""

    def __init__(self):
        self.clients: Dict[str, Any] = {}
        self.configs: Dict[str, LLMModelConfig] = {}
        self.current_model: Optional[str] = None

    def initialize_client(self, model_config: LLMModelConfig) -> Any:
        """初始化LLM客户端"""
        try:
            provider = model_config.provider

            if provider == ModelProvider.OPENAI:
                client = OpenAI(
                    api_key=model_config.api_key,
                    base_url=model_config.base_url or "https://api.openai.com/v1",
                    timeout=model_config.timeout
                )

            elif provider == ModelProvider.AZURE:
                client = AzureOpenAI(
                    api_key=model_config.api_key,
                    api_version=model_config.api_version,
                    azure_endpoint=model_config.base_url,
                    timeout=model_config.timeout
                )

            elif provider in [ModelProvider.DEEPSEEK,
                              ModelProvider.QWEN, ModelProvider.OLLAMA, ModelProvider.CUSTOM]:
                # 使用通用的OpenAI客户端（兼容OpenAI API格式）
                client = OpenAI(
                    api_key=model_config.api_key,
                    base_url=model_config.base_url,
                    timeout=model_config.timeout
                )

            else:
                raise ValueError(f"不支持的模型提供商: {provider}")

            return client

        except Exception as e:
            raise ValueError(f"初始化 {model_config.name} 客户端失败: {e}")

    def add_model(self, model_config: LLMModelConfig) -> bool:
        """添加模型配置和客户端"""
        try:
            client = self.initialize_client(model_config)
            self.clients[model_config.name] = client
            self.configs[model_config.name] = model_config

            # 如果没有当前模型，设置为第一个添加的模型
            if self.current_model is None:
                self.current_model = model_config.name

            return True

        except Exception as e:
            raise ValueError(f"添加模型 {model_config.name} 失败: {e}")

    def set_current_model(self, model_name: str) -> bool:
        """设置当前模型"""
        if model_name in self.clients:
            self.current_model = model_name
            return True
        return False

    def get_current_client(self) -> Optional[Any]:
        """获取当前客户端"""
        if self.current_model:
            return self.clients.get(self.current_model)
        return None

    def get_current_config(self) -> Optional[LLMModelConfig]:
        """获取当前配置"""
        if self.current_model:
            return self.configs.get(self.current_model)
        return None

    def test_connection(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """测试连接"""
        model_to_test = model_name or self.current_model
        try:
            if not model_to_test:
                return {"success": False, "error": "没有可用的模型"}

            client = self.clients.get(model_to_test)
            if not client:
                return {"success": False, "error": f"模型 '{model_to_test}' 未初始化"}

            # 发送一个简单的测试请求
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_to_test,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            end_time = time.time()

            return {
                "success": True,
                "model": model_to_test,
                "response_time": end_time - start_time,
                "response": response.choices[0].message.content if response.choices else ""
            }

        except Exception as e:
            return {"success": False, "error": str(e), "model": model_to_test}

    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取所有可用模型"""
        models = []
        for name, config in self.configs.items():
            models.append({
                "name": name,
                "provider": config.provider.value,
                "enabled": config.enabled,
                "description": config.description
            })
        return models

    def clear(self):
        """清除所有客户端和配置"""
        self.clients.clear()
        self.configs.clear()
        self.current_model = None

    def chat_completion(self, messages: List[ChatCompletionMessageParam],
                        stream: bool = False, **kwargs) -> Any:
        """
        调用聊天补全API

        Args:
            messages: 消息列表
            stream: 是否使用流式响应
            **kwargs: 其他参数

        Returns:
            API响应
        """
        client = self.get_current_client()
        if not client:
            raise ValueError("没有可用的LLM客户端")

        config = self.get_current_config()
        if not config:
            raise ValueError("没有可用的模型配置")

        # 准备请求参数
        request_params = {
            "model": config.name,
            "messages": messages,
            "stream": stream,
            "temperature": kwargs.get("temperature", config.temperature),
            "max_tokens": kwargs.get("max_tokens", config.max_tokens),
            "timeout": kwargs.get("timeout", config.timeout)
        }

        # 添加可选参数
        optional_params = ["top_p", "frequency_penalty", "presence_penalty", "stop"]
        for param in optional_params:
            if param in kwargs:
                request_params[param] = kwargs[param]

        try:
            response = client.chat.completions.create(**request_params)
            return response

        except Exception as e:
            raise ValueError(f"API调用失败: {e}")
