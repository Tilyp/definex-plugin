"""
增强版LLM客户端管理器
继承基础LLM客户端，添加文本清理和响应转换功能
"""

from typing import Dict, List, Any

from openai.types.chat import ChatCompletionMessageParam

from definex.core.config_models import LLMModelConfig
from definex.core.llm_client_base import LLMClientBase
from definex.exception.exceptions import ConfigException
from definex.plugin.chat.text_utils import TextCleaner


class EnhancedLLMClientManager(LLMClientBase):
    """增强版LLM客户端管理器 - 用于Chat模块"""

    def __init__(self):
        """初始化增强版LLM客户端管理器"""
        super().__init__()
        self.text_cleaner = TextCleaner()

    def initialize_client(self, model_config: LLMModelConfig) -> Any:
        """初始化LLM客户端（重写以使用ConfigException）"""
        try:
            return super().initialize_client(model_config)
        except Exception as e:
            raise ConfigException(f"初始化 {model_config.name} 客户端失败: {e}")

    def add_model(self, model_config: LLMModelConfig) -> bool:
        """添加模型配置和客户端（重写以使用ConfigException）"""
        try:
            return super().add_model(model_config)
        except Exception as e:
            raise ConfigException(f"添加模型 {model_config.name} 失败: {e}")

    def chat_completion(self, messages: List[ChatCompletionMessageParam],
                        stream: bool = False, **kwargs) -> Any:
        """
        调用聊天补全API，包含编码修复

        Args:
            messages: 消息列表
            stream: 是否使用流式响应
            **kwargs: 其他参数

        Returns:
            API响应字典
        """
        client = self.get_current_client()
        if not client:
            raise ConfigException("没有可用的LLM客户端")

        config = self.get_current_config()
        if not config:
            raise ConfigException("没有可用的模型配置")

        # 清理消息中的文本
        cleaned_messages = []
        for msg in messages:
            try:
                role = msg["role"]
                content = msg["content"]
                # 清理内容
                if isinstance(content, str):
                    content = self.text_cleaner.escape_json_special_chars(content)
                    cleaned_content = self.text_cleaner.clean_unicode(content, "ignore")
                else:
                    cleaned_content = content
                cleaned_messages.append({"role": role, "content": cleaned_content})
            except Exception as e:
                # 如果清理失败，使用原始消息
                cleaned_messages.append(msg)

        # 准备请求参数
        request_params = {
            "model": config.name,
            "messages": cleaned_messages,
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
            response_dict = self._convert_response_to_dict(response)
            return response_dict

        except Exception as e:
            # 处理特定的编码错误
            error_msg = str(e)
            if "surrogates not allowed" in error_msg or "utf-8" in error_msg.lower():
                raise ConfigException(f"API响应包含非法字符，请尝试清理输入或联系API提供商: {error_msg}")
            raise ConfigException(f"API调用失败: {e}")

    def _convert_response_to_dict(self, response) -> Dict[str, Any]:
        """将OpenAI响应对象转换为字典"""
        try:
            # 方法1：使用对象的 model_dump() 方法（Pydantic v2）
            if hasattr(response, 'model_dump'):
                result = response.model_dump()
                # 清理文本
                if result.get('choices') and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    if choice.get('message') and choice['message'].get('content'):
                        choice['message']['content'] = self.text_cleaner.clean_unicode(
                            choice['message']['content'], "ignore"
                        )
                return result

            # 方法2：使用对象的 dict() 方法（Pydantic v1）
            elif hasattr(response, 'dict'):
                result = response.dict()
                # 清理文本
                if result.get('choices') and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    if choice.get('message') and choice['message'].get('content'):
                        choice['message']['content'] = self.text_cleaner.clean_unicode(
                            choice['message']['content'], "ignore"
                        )
                return result

            # 方法3：直接返回响应对象
            else:
                return response

        except Exception as e:
            raise ConfigException(f"转换响应失败: {e}")
