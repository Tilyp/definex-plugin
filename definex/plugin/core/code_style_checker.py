"""
简化版代码规范检查器
专门检查 action 方法参数是否使用 Annotated 类型注解
"""

import inspect
from pathlib import Path
from typing import List, Dict, Any, get_origin, get_args


class ActionStyleChecker:
    """Action 方法规范检查器"""

    @staticmethod
    def check_action_method(method) -> List[Dict[str, Any]]:
        """
        检查单个 action 方法

        Args:
            method: 要检查的方法

        Returns:
            检查结果列表
        """
        issues = []

        # 获取方法签名
        sig = inspect.signature(method)

        # 获取类型提示
        try:
            hints = inspect.get_annotations(method)
        except Exception:
            hints = {}

        # 检查参数注解
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_type = hints.get(param_name)

            if param_type is None:
                # 缺少类型注解
                issues.append({
                    "rule": "parameter_annotation",
                    "level": "error",
                    "message": f"参数 '{param_name}' 缺少类型注解",
                    "param": param_name
                })
            else:
                # 检查是否是 Annotated 类型
                origin = get_origin(param_type)

                # 检查是否是 Annotated 类型
                is_annotated = False
                if origin is not None:
                    # 检查是否是 typing._AnnotatedAlias 或 Annotated
                    try:
                        from typing import _AnnotatedAlias
                        if isinstance(param_type, _AnnotatedAlias):
                            is_annotated = True
                    except ImportError:
                        # 回退方法：检查字符串表示
                        if 'Annotated' in str(origin):
                            is_annotated = True

                if not is_annotated:
                    # 不是 Annotated 类型，报告错误
                    issues.append({
                        "rule": "parameter_annotation",
                        "level": "error",
                        "message": f"参数 '{param_name}' 必须使用 Annotated类型注解",
                        "param": param_name
                    })
                else:
                    # 检查是否有描述
                    try:
                        args = get_args(param_type)
                        if len(args) < 2 or not isinstance(args[1], str):
                            issues.append({
                                "rule": "parameter_description",
                                "level": "error",
                                "message": f"参数 '{param_name}' 的 Annotated 注解缺少描述",
                                "param": param_name
                            })
                    except Exception:
                        pass

        # 检查返回类型注解
        if 'return' not in hints:
            issues.append({
                "rule": "return_annotation",
                "level": "warning",
                "message": "方法缺少返回类型注解"
            })

        # 检查文档字符串
        docstring = inspect.getdoc(method)
        if not docstring:
            issues.append({
                "rule": "docstring",
                "level": "warning",
                "message": "方法缺少文档字符串"
            })

        # 检查异步标记
        if not inspect.iscoroutinefunction(method):
            issues.append({
                "rule": "async_marker",
                "level": "info",
                "message": "考虑使用 async 定义异步方法"
            })

        return issues

    @staticmethod
    def check_file(file_path: Path) -> Dict[str, Any]:
        """
        检查文件中的所有 action 方法

        Args:
            file_path: 文件路径

        Returns:
            检查结果
        """
        import importlib.util

        results = {
            "file": str(file_path),
            "total_actions": 0,
            "issues": [],
            "summary": {
                "error": 0,
                "warning": 0,
                "info": 0
            }
        }

        try:
            # 动态加载模块
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找所有继承 BasePlugin 的类
            from definex.plugin.sdk import BasePlugin

            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, BasePlugin) and
                    obj is not BasePlugin):

                    # 检查类中的所有 action 方法
                    for method_name, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                        if hasattr(method, '_is_action'):
                            results["total_actions"] += 1
                            method_issues = ActionStyleChecker.check_action_method(method)

                            for issue in method_issues:
                                issue["method"] = f"{name}.{method_name}"
                                results["issues"].append(issue)

                                # 更新统计
                                level = issue["level"]
                                if level in results["summary"]:
                                    results["summary"][level] += 1

        except Exception as e:
            results["error"] = str(e)

        return results
