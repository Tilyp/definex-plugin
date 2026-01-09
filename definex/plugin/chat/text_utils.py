"""
文本处理工具，处理编码和特殊字符问题
"""
import re
import unicodedata

class TextCleaner:
    """文本清理工具"""

    @staticmethod
    def clean_unicode(text: str, method: str = "ignore") -> str:
        """
        清理Unicode字符
        Args:
            text: 输入文本
            method: 清理方法，可选值：
                - "ignore": 忽略无法编码的字符
                - "replace": 替换为问号
                - "normalize": Unicode规范化
                - "remove_surrogates": 移除代理对字符

        Returns:
            清理后的文本
        """
        if not text:
            return text

        if method == "ignore":
            try:
                return text.encode('utf-8', 'ignore').decode('utf-8')
            except:
                # 回退到逐字符处理
                return ''.join(c for c in text if ord(c) < 0x10000)

        elif method == "replace":
            try:
                return text.encode('utf-8', 'replace').decode('utf-8')
            except:
                return ''.join(c if ord(c) < 0x10000 else '?' for c in text)

        elif method == "normalize":
            # Unicode规范化
            try:
                text =  unicodedata.normalize('NFKD', text)
                return text.encode('utf-8', 'ignore').decode('utf-8')
            except:
                return text

        elif method == "remove_surrogates":
            # 移除代理对字符 (U+D800 to U+DFFF)
            return ''.join(
                c for c in text
                if not ('\ud800' <= c <= '\udfff')
            )

        else:
            # 默认使用ignore
            try:
                return text.encode('utf-8', 'ignore').decode('utf-8')
            except:
                return text

    @staticmethod
    def escape_json_special_chars(text: str) -> str:
        """转义JSON特殊字符"""
        if not text:
            return text

        # 常见的需要转义的字符
        replacements = {
            '\\': '\\\\',  # 反斜杠
            '"': '\\"',    # 双引号
            '\b': '\\b',   # 退格
            '\f': '\\f',   # 换页
            '\n': '\\n',   # 换行
            '\r': '\\r',   # 回车
            '\t': '\\t',   # 制表符
            # 处理Unicode控制字符
            '\u0000': '\\u0000',
            '\u0001': '\\u0001',
            # 添加其他需要转义的字符...
        }

        # 逐步替换
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)

        # 处理其他不可打印字符
        result = ''.join(char for char in result if ord(char) >= 32 or char in '\n\r\t')
        return result

    @staticmethod
    def safe_markdown(text: str, max_length: int = 1000) -> str:
        """安全转换为Markdown文本"""
        try:
            # 先清理文本
            cleaned = TextCleaner.clean_unicode(text, "remove_surrogates")

            # 限制长度
            if len(cleaned) > max_length:
                cleaned = cleaned[:max_length] + "..."

            return cleaned
        except Exception:
            # 如果清理失败，返回安全的纯文本
            return text[:500] + "..." if len(text) > 500 else text

    @staticmethod
    def extract_code_blocks_safe(text: str) -> list:
        """安全提取代码块"""
        try:
            # 清理文本后提取
            cleaned_text = TextCleaner.clean_unicode(text, "ignore")

            # 匹配代码块
            pattern = r"```(?:\w+)?\s*\n(.*?)\n\s*```"
            matches = re.findall(pattern, cleaned_text, re.DOTALL)

            # 进一步清理每个代码块
            cleaned_blocks = []
            for code in matches:
                if code:
                    cleaned_code = TextCleaner.clean_unicode(code.strip(), "ignore")
                    if cleaned_code:
                        cleaned_blocks.append(cleaned_code)

            return cleaned_blocks

        except Exception:
            return []

    @staticmethod
    def sanitize_for_yaml(text: str) -> str:
        """为YAML文件清理文本"""
        if not text:
            return text

        # 移除控制字符和代理对
        cleaned = ''.join(
            c for c in text
            if c.isprintable() and not ('\ud800' <= c <= '\udfff')
        )

        # 处理引号
        cleaned = cleaned.replace('"', "'")

        # 限制长度
        if len(cleaned) > 10000:
            cleaned = cleaned[:10000] + "..."

        return cleaned