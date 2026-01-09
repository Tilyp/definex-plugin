"""
TODO生成器模块 - 自动从需求生成TODO任务列表
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class TODOTask:
    """TODO任务类"""

    def __init__(self, title: str, description: str = "", priority: str = "medium",
                 dependencies: List[str] = None, estimated_time: str = ""):
        self.title = title
        self.description = description
        self.priority = priority  # low, medium, high
        self.dependencies = dependencies or []
        self.estimated_time = estimated_time
        self.completed = False
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.subtasks: List[TODOTask] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "estimated_time": self.estimated_time,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks]
        }

    def mark_completed(self):
        """标记为完成"""
        self.completed = True
        self.completed_at = datetime.now()

    def add_subtask(self, subtask: "TODOTask"):
        """添加子任务"""
        self.subtasks.append(subtask)


class TODOGenerator:
    """TODO生成器"""

    def __init__(self):
        self.tasks: List[TODOTask] = []
        self.project_name = ""
        self.project_path = ""

    def generate_from_requirements(self, requirements: str, project_info: Dict[str, Any]) -> List[TODOTask]:
        """
        从需求生成TODO任务

        Args:
            requirements: 需求描述
            project_info: 项目信息

        Returns:
            TODO任务列表
        """
        self.project_name = project_info.get("name", "未知项目")
        self.project_path = project_info.get("path", "")

        # 清空现有任务
        self.tasks = []

        # 分析需求类型
        requirement_type = self._analyze_requirement_type(requirements)

        # 根据需求类型生成不同的TODO结构
        if requirement_type == "plugin_development":
            self._generate_plugin_development_tasks(requirements, project_info)
        elif requirement_type == "feature_addition":
            self._generate_feature_addition_tasks(requirements, project_info)
        elif requirement_type == "bug_fix":
            self._generate_bug_fix_tasks(requirements, project_info)
        elif requirement_type == "refactoring":
            self._generate_refactoring_tasks(requirements, project_info)
        else:
            self._generate_general_tasks(requirements, project_info)

        return self.tasks

    def _analyze_requirement_type(self, requirements: str) -> str:
        """分析需求类型"""
        requirements_lower = requirements.lower()

        if any(word in requirements_lower for word in ["插件", "plugin", "扩展", "extension"]):
            return "plugin_development"
        elif any(word in requirements_lower for word in ["功能", "feature", "添加", "增加", "实现"]):
            return "feature_addition"
        elif any(word in requirements_lower for word in ["bug", "错误", "修复", "问题", "故障"]):
            return "bug_fix"
        elif any(word in requirements_lower for word in ["重构", "refactor", "优化", "改进"]):
            return "refactoring"
        else:
            return "general"

    def _generate_plugin_development_tasks(self, requirements: str, project_info: Dict[str, Any]) -> None:
        """生成插件开发TODO任务"""
        # 主任务：开发插件
        main_task = TODOTask(
            title=f"开发插件: {self.project_name}",
            description=f"根据需求开发插件: {requirements[:100]}...",
            priority="high",
            estimated_time="2-4周"
        )

        # 子任务
        subtasks = [
            TODOTask(
                title="需求分析和澄清",
                description="详细分析需求，澄清模糊点，确认功能范围",
                priority="high",
                estimated_time="1-2天"
            ),
            TODOTask(
                title="设计插件架构",
                description="设计插件整体架构，包括类结构、接口设计",
                priority="high",
                estimated_time="2-3天"
            ),
            TODOTask(
                title="实现核心功能",
                description="实现插件的核心功能模块",
                priority="high",
                estimated_time="1-2周"
            ),
            TODOTask(
                title="编写测试用例",
                description="为插件功能编写单元测试和集成测试",
                priority="medium",
                estimated_time="3-5天"
            ),
            TODOTask(
                title="编写文档",
                description="编写插件使用文档、API文档和示例",
                priority="medium",
                estimated_time="2-3天"
            ),
            TODOTask(
                title="测试和调试",
                description="进行全面测试，修复发现的问题",
                priority="high",
                estimated_time="3-5天"
            ),
            TODOTask(
                title="打包和发布",
                description="打包插件，准备发布到插件市场",
                priority="medium",
                estimated_time="1-2天"
            )
        ]

        # 添加子任务
        for subtask in subtasks:
            main_task.add_subtask(subtask)

        self.tasks.append(main_task)

    def _generate_feature_addition_tasks(self, requirements: str, project_info: Dict[str, Any]) -> None:
        """生成功能添加TODO任务"""
        # 提取功能关键词
        feature_keywords = self._extract_keywords(requirements)

        main_task = TODOTask(
            title=f"添加功能: {'、'.join(feature_keywords[:3])}",
            description=f"为项目添加新功能: {requirements[:100]}...",
            priority="high",
            estimated_time="1-2周"
        )

        subtasks = [
            TODOTask(
                title="功能需求分析",
                description="分析功能需求，确定实现方案",
                priority="high",
                estimated_time="1-2天"
            ),
            TODOTask(
                title="设计功能架构",
                description="设计功能模块架构和接口",
                priority="high",
                estimated_time="2-3天"
            ),
            TODOTask(
                title="实现功能代码",
                description="编写功能实现代码",
                priority="high",
                estimated_time="3-5天"
            ),
            TODOTask(
                title="集成测试",
                description="测试新功能与现有系统的集成",
                priority="medium",
                estimated_time="2-3天"
            ),
            TODOTask(
                title="更新文档",
                description="更新项目文档，添加新功能说明",
                priority="medium",
                estimated_time="1-2天"
            )
        ]

        for subtask in subtasks:
            main_task.add_subtask(subtask)

        self.tasks.append(main_task)

    def _generate_bug_fix_tasks(self, requirements: str, project_info: Dict[str, Any]) -> None:
        """生成Bug修复TODO任务"""
        main_task = TODOTask(
            title="修复Bug",
            description=f"修复问题: {requirements[:100]}...",
            priority="high",
            estimated_time="3-5天"
        )

        subtasks = [
            TODOTask(
                title="问题重现",
                description="重现报告的问题，确认Bug存在",
                priority="high",
                estimated_time="0.5-1天"
            ),
            TODOTask(
                title="问题定位",
                description="定位问题根源，分析原因",
                priority="high",
                estimated_time="1-2天"
            ),
            TODOTask(
                title="修复方案设计",
                description="设计修复方案，评估影响范围",
                priority="high",
                estimated_time="1天"
            ),
            TODOTask(
                title="实施修复",
                description="编写修复代码",
                priority="high",
                estimated_time="1-2天"
            ),
            TODOTask(
                title="测试验证",
                description="测试修复效果，确保问题解决",
                priority="high",
                estimated_time="1天"
            )
        ]

        for subtask in subtasks:
            main_task.add_subtask(subtask)

        self.tasks.append(main_task)

    def _generate_refactoring_tasks(self, requirements: str, project_info: Dict[str, Any]) -> None:
        """生成重构TODO任务"""
        main_task = TODOTask(
            title="代码重构",
            description=f"重构代码: {requirements[:100]}...",
            priority="medium",
            estimated_time="1-2周"
        )

        subtasks = [
            TODOTask(
                title="代码分析",
                description="分析现有代码，识别需要重构的部分",
                priority="medium",
                estimated_time="2-3天"
            ),
            TODOTask(
                title="重构方案设计",
                description="设计重构方案，制定重构计划",
                priority="medium",
                estimated_time="2-3天"
            ),
            TODOTask(
                title="逐步重构",
                description="按照计划逐步实施重构",
                priority="medium",
                estimated_time="3-5天"
            ),
            TODOTask(
                title="测试验证",
                description="测试重构后的代码，确保功能正常",
                priority="high",
                estimated_time="2-3天"
            )
        ]

        for subtask in subtasks:
            main_task.add_subtask(subtask)

        self.tasks.append(main_task)

    def _generate_general_tasks(self, requirements: str, project_info: Dict[str, Any]) -> None:
        """生成通用TODO任务"""
        main_task = TODOTask(
            title=f"实现需求: {requirements[:50]}...",
            description=requirements,
            priority="medium",
            estimated_time="1-2周"
        )

        subtasks = [
            TODOTask(
                title="需求分析",
                description="分析需求，制定实现计划",
                priority="high",
                estimated_time="1-2天"
            ),
            TODOTask(
                title="设计实现方案",
                description="设计技术方案和架构",
                priority="high",
                estimated_time="2-3天"
            ),
            TODOTask(
                title="编码实现",
                description="编写实现代码",
                priority="high",
                estimated_time="3-5天"
            ),
            TODOTask(
                title="测试验证",
                description="测试功能，确保符合需求",
                priority="medium",
                estimated_time="2-3天"
            )
        ]

        for subtask in subtasks:
            main_task.add_subtask(subtask)

        self.tasks.append(main_task)

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'[\u4e00-\u9fff\w]+', text.lower())

        # 过滤常见词
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
        keywords = [word for word in words if word not in stop_words and len(word) > 1]

        return list(set(keywords))[:10]  # 返回前10个唯一关键词

    def save_to_file(self, file_path: Path) -> bool:
        """保存TODO到文件"""
        try:
            data = {
                "project_name": self.project_name,
                "project_path": self.project_path,
                "generated_at": datetime.now().isoformat(),
                "tasks": [task.to_dict() for task in self.tasks]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存TODO失败: {e}")
            return False

    def load_from_file(self, file_path: Path) -> bool:
        """从文件加载TODO"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)

            self.project_name = data.get("project_name", "")
            self.project_path = data.get("project_path", "")

            # 重新构建任务对象
            self.tasks = []
            for task_data in data.get("tasks", []):
                task = self._dict_to_task(task_data)
                self.tasks.append(task)

            return True
        except Exception as e:
            print(f"加载TODO失败: {e}")
            return False

    def _dict_to_task(self, task_data: Dict[str, Any]) -> TODOTask:
        """从字典创建任务对象"""
        task = TODOTask(
            title=task_data["title"],
            description=task_data.get("description", ""),
            priority=task_data.get("priority", "medium"),
            dependencies=task_data.get("dependencies", []),
            estimated_time=task_data.get("estimated_time", "")
        )

        task.completed = task_data.get("completed", False)
        task.created_at = datetime.fromisoformat(task_data["created_at"])

        if task_data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(task_data["completed_at"])

        # 递归创建子任务
        for subtask_data in task_data.get("subtasks", []):
            subtask = self._dict_to_task(subtask_data)
            task.add_subtask(subtask)

        return task

    def format_for_display(self) -> str:
        """格式化TODO用于显示"""
        if not self.tasks:
            return "暂无TODO任务"

        output = []
        output.append(f"# TODO: {self.project_name}")
        output.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"项目路径: {self.project_path}")
        output.append("")

        for i, task in enumerate(self.tasks, 1):
            status = "✅" if task.completed else "◻️"
            priority_icon = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(task.priority, "⚪")

            output.append(f"{status} {priority_icon} {i}. {task.title}")
            if task.description:
                output.append(f"   📝 {task.description}")
            if task.estimated_time:
                output.append(f"   ⏱️  预计时间: {task.estimated_time}")

            # 显示子任务
            if task.subtasks:
                output.append("   子任务:")
                for j, subtask in enumerate(task.subtasks, 1):
                    subtask_status = "✅" if subtask.completed else "◻️"
                    output.append(f"     {subtask_status} {j}. {subtask.title}")

            output.append("")

        return "\n".join(output)

    def format_for_markdown(self) -> str:
        """生成Markdown格式的TODO"""
        if not self.tasks:
            return "# TODO\n\n暂无任务"

        output = []
        output.append(f"# TODO: {self.project_name}")
        output.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"**项目路径**: `{self.project_path}`")
        output.append("\n---\n")

        for i, task in enumerate(self.tasks, 1):
            status = "✅" if task.completed else "◻️"
            priority_badge = {
                "high": "🔴 **高优先级**",
                "medium": "🟡 **中优先级**",
                "low": "🟢 **低优先级**"
            }.get(task.priority, "⚪ 未知优先级")

            output.append(f"## {status} {i}. {task.title}")
            output.append(f"\n**优先级**: {priority_badge}")

            if task.description:
                output.append(f"\n**描述**: {task.description}")

            if task.estimated_time:
                output.append(f"\n**预计时间**: {task.estimated_time}")

            if task.dependencies:
                output.append(f"\n**依赖**: {', '.join(task.dependencies)}")

            # 子任务
            if task.subtasks:
                output.append("\n**子任务**:")
                for j, subtask in enumerate(task.subtasks, 1):
                    subtask_status = "✅" if subtask.completed else "◻️"
                    output.append(f"- {subtask_status} {subtask.title}")
                    if subtask.description:
                        output.append(f"  - {subtask.description}")

            output.append("\n---\n")

        return "\n".join(output)
