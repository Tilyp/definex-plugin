"""
代码生成流程管理器 - 管理完整的代码生成流程
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any

from definex.plugin.chat.prompt_builder import (
    PromptConfig,
    SystemPromptBuilder
)


class FlowStage(Enum):
    """流程阶段"""
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    INTENT_RECOGNITION = "intent_recognition"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODE_GENERATION = "code_generation"
    TEST_GENERATION = "test_generation"
    TEST_REGRESSION = "test_regression"
    CLEANUP = "cleanup"
    DOCUMENTATION = "documentation"
    COMPLETED = "completed"


@dataclass
class FlowContext:
    """流程上下文"""
    # 项目信息
    project_path: str
    project_name: str

    # 阶段数据
    current_stage: FlowStage = FlowStage.REQUIREMENT_ANALYSIS
    stage_data: Dict[FlowStage, Dict[str, Any]] = field(default_factory=dict)

    # 用户输入
    user_requirements: str = ""
    clarified_requirements: str = ""

    # 生成结果
    architecture_design: str = ""
    generated_code: str = ""
    test_code: str = ""
    test_results: str = ""
    documentation: str = ""

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "current_stage": self.current_stage.value,
            "stage_data": {
                stage.value: data
                for stage, data in self.stage_data.items()
            },
            "user_requirements": self.user_requirements,
            "clarified_requirements": self.clarified_requirements,
            "architecture_design": self.architecture_design,
            "generated_code": self.generated_code,
            "test_code": self.test_code,
            "test_results": self.test_results,
            "documentation": self.documentation,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed": self.completed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowContext":
        """从字典创建"""
        context = cls(
            project_path=data["project_path"],
            project_name=data["project_name"]
        )

        context.current_stage = FlowStage(data["current_stage"])
        context.stage_data = {
            FlowStage(stage): stage_data
            for stage, stage_data in data.get("stage_data", {}).items()
        }

        context.user_requirements = data.get("user_requirements", "")
        context.clarified_requirements = data.get("clarified_requirements", "")
        context.architecture_design = data.get("architecture_design", "")
        context.generated_code = data.get("generated_code", "")
        context.test_code = data.get("test_code", "")
        context.test_results = data.get("test_results", "")
        context.documentation = data.get("documentation", "")

        context.created_at = datetime.fromisoformat(data["created_at"])
        context.updated_at = datetime.fromisoformat(data["updated_at"])
        context.completed = data.get("completed", False)

        return context


class CodeFlowManager:
    """代码生成流程管理器"""

    def __init__(self, project_path: str, project_name: str = None):
        """
        初始化流程管理器

        Args:
            project_path: 项目路径
            project_name: 项目名称，如果为None则从路径提取
        """
        self.project_path = project_path
        self.project_name = project_name or os.path.basename(project_path)

        # 初始化上下文
        self.context = FlowContext(
            project_path=project_path,
            project_name=self.project_name
        )

        # 初始化提示词构建器
        self.prompt_builder = SystemPromptBuilder()

        # 流程状态
        self.is_running = False
        self.current_task = None

    def start_flow(self, user_requirements: str) -> Dict[str, Any]:
        """
        开始代码生成流程

        Args:
            user_requirements: 用户需求描述

        Returns:
            流程启动结果
        """
        if self.is_running:
            return {
                "success": False,
                "error": "流程已经在运行中",
                "current_stage": self.context.current_stage.value
            }

        self.is_running = True
        self.context.user_requirements = user_requirements
        self.context.current_stage = FlowStage.REQUIREMENT_ANALYSIS
        self.context.updated_at = datetime.now()

        # 保存上下文
        self._save_context()

        return {
            "success": True,
            "message": "流程已启动",
            "current_stage": self.context.current_stage.value,
            "next_action": "开始需求分析"
        }

    def proceed_to_next_stage(self) -> Dict[str, Any]:
        """
        进入下一个阶段

        Returns:
            阶段切换结果
        """
        if not self.is_running:
            return {
                "success": False,
                "error": "流程未启动"
            }

        # 获取下一个阶段
        next_stage = self._get_next_stage(self.context.current_stage)

        if next_stage == self.context.current_stage:
            return {
                "success": False,
                "error": "已经是最后一个阶段",
                "current_stage": self.context.current_stage.value
            }

        # 更新阶段
        self.context.current_stage = next_stage
        self.context.updated_at = datetime.now()

        # 保存上下文
        self._save_context()

        return {
            "success": True,
            "message": f"已进入{self._get_stage_name(next_stage)}阶段",
            "current_stage": next_stage.value,
            "stage_name": self._get_stage_name(next_stage)
        }

    def get_current_prompt_config(self) -> PromptConfig:
        """
        获取当前阶段的提示词配置

        Returns:
            提示词配置
        """
        stage_to_config = {
            FlowStage.REQUIREMENT_ANALYSIS: self.prompt_builder.get_requirement_analysis_config,
            FlowStage.INTENT_RECOGNITION: self.prompt_builder.get_intent_recognition_config,
            FlowStage.ARCHITECTURE_DESIGN: self.prompt_builder.get_architecture_design_config,
            FlowStage.CODE_GENERATION: self.prompt_builder.get_code_generation_config,
            FlowStage.TEST_GENERATION: self.prompt_builder.get_test_generation_config,
            FlowStage.TEST_REGRESSION: self.prompt_builder.get_test_regression_config,
            FlowStage.CLEANUP: self.prompt_builder.get_cleanup_config,
            FlowStage.DOCUMENTATION: self.prompt_builder.get_documentation_config,
        }

        config_func = stage_to_config.get(self.context.current_stage)
        if config_func:
            return config_func()
        else:
            return self.prompt_builder.get_chat_config()

    def get_context_vars(self, conversation_summary: str = "") -> Dict[str, str]:
        """
        获取上下文变量

        Args:
            conversation_summary: 对话摘要

        Returns:
            上下文变量字典
        """
        context_vars = {
            "project_context": self._get_project_context(),
            "conversation_summary": conversation_summary
        }

        # 根据当前阶段添加特定变量
        if self.context.current_stage == FlowStage.REQUIREMENT_ANALYSIS:
            context_vars["user_requirement"] = self.context.user_requirements

        elif self.context.current_stage == FlowStage.ARCHITECTURE_DESIGN:
            context_vars["requirements_summary"] = self.context.clarified_requirements

        elif self.context.current_stage == FlowStage.CODE_GENERATION:
            context_vars["architecture_design"] = self.context.architecture_design

        elif self.context.current_stage == FlowStage.TEST_GENERATION:
            context_vars["generated_code"] = self.context.generated_code

        elif self.context.current_stage == FlowStage.TEST_REGRESSION:
            context_vars["test_results"] = self.context.test_results

        elif self.context.current_stage == FlowStage.CLEANUP:
            context_vars["project_structure"] = self._get_project_structure()

        elif self.context.current_stage == FlowStage.DOCUMENTATION:
            context_vars["project_info"] = self._get_project_info()

        return context_vars

    def update_stage_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新阶段结果

        Args:
            result: 阶段结果

        Returns:
            更新结果
        """
        stage = self.context.current_stage

        # 保存阶段数据
        if stage not in self.context.stage_data:
            self.context.stage_data[stage] = {}

        self.context.stage_data[stage].update(result)
        self.context.updated_at = datetime.now()

        # 根据阶段类型保存特定数据
        if stage == FlowStage.REQUIREMENT_ANALYSIS:
            if "clarified_requirements" in result:
                self.context.clarified_requirements = result["clarified_requirements"]

        elif stage == FlowStage.ARCHITECTURE_DESIGN:
            if "architecture_design" in result:
                self.context.architecture_design = result["architecture_design"]

        elif stage == FlowStage.CODE_GENERATION:
            if "generated_code" in result:
                self.context.generated_code = result["generated_code"]

        elif stage == FlowStage.TEST_GENERATION:
            if "test_code" in result:
                self.context.test_code = result["test_code"]

        elif stage == FlowStage.TEST_REGRESSION:
            if "test_results" in result:
                self.context.test_results = result["test_results"]

        elif stage == FlowStage.DOCUMENTATION:
            if "documentation" in result:
                self.context.documentation = result["documentation"]
                # 文档生成完成，标记流程完成
                self.context.completed = True
                self.is_running = False

        # 保存上下文
        self._save_context()

        return {
            "success": True,
            "message": f"{self._get_stage_name(stage)}结果已保存",
            "current_stage": stage.value
        }

    def get_flow_status(self) -> Dict[str, Any]:
        """
        获取流程状态

        Returns:
            流程状态信息
        """
        return {
            "is_running": self.is_running,
            "current_stage": self.context.current_stage.value,
            "stage_name": self._get_stage_name(self.context.current_stage),
            "completed_stages": [
                stage.value for stage in self.context.stage_data.keys()
            ],
            "progress": self._calculate_progress(),
            "created_at": self.context.created_at.isoformat(),
            "updated_at": self.context.updated_at.isoformat(),
            "completed": self.context.completed
        }

    def reset_flow(self) -> Dict[str, Any]:
        """
        重置流程

        Returns:
            重置结果
        """
        self.context = FlowContext(
            project_path=self.project_path,
            project_name=self.project_name
        )
        self.is_running = False

        # 删除保存的上下文文件
        context_file = self._get_context_file_path()
        if os.path.exists(context_file):
            os.remove(context_file)

        return {
            "success": True,
            "message": "流程已重置"
        }

    # 私有方法

    def _get_next_stage(self, current_stage: FlowStage) -> FlowStage:
        """获取下一个阶段"""
        stages = [
            FlowStage.REQUIREMENT_ANALYSIS,
            FlowStage.INTENT_RECOGNITION,
            FlowStage.ARCHITECTURE_DESIGN,
            FlowStage.CODE_GENERATION,
            FlowStage.TEST_GENERATION,
            FlowStage.TEST_REGRESSION,
            FlowStage.CLEANUP,
            FlowStage.DOCUMENTATION,
            FlowStage.COMPLETED
        ]

        try:
            current_index = stages.index(current_stage)
            if current_index + 1 < len(stages):
                return stages[current_index + 1]
            else:
                return current_stage
        except ValueError:
            return FlowStage.REQUIREMENT_ANALYSIS

    def _get_stage_name(self, stage: FlowStage) -> str:
        """获取阶段名称"""
        stage_names = {
            FlowStage.REQUIREMENT_ANALYSIS: "需求分析",
            FlowStage.INTENT_RECOGNITION: "意图识别",
            FlowStage.ARCHITECTURE_DESIGN: "架构设计",
            FlowStage.CODE_GENERATION: "代码生成",
            FlowStage.TEST_GENERATION: "测试生成",
            FlowStage.TEST_REGRESSION: "测试回归",
            FlowStage.CLEANUP: "清理测试文件",
            FlowStage.DOCUMENTATION: "生成文档",
            FlowStage.COMPLETED: "已完成"
        }
        return stage_names.get(stage, "未知阶段")

    def _calculate_progress(self) -> float:
        """计算进度百分比"""
        total_stages = 8  # 从需求分析到文档生成共8个阶段
        completed_stages = len(self.context.stage_data)

        if self.context.completed:
            return 100.0

        return min(100.0, (completed_stages / total_stages) * 100)

    def _get_project_context(self) -> str:
        """获取项目上下文"""
        try:
            # 读取项目文件
            files = []
            for root, dirs, filenames in os.walk(self.project_path):
                for filename in filenames:
                    if filename.endswith('.py'):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                                files.append(f"文件: {filename}\n{content[:500]}...")
                        except:
                            continue

            return "\n".join(files[:5])  # 限制文件数量
        except:
            return "无法读取项目上下文"

    def _get_project_structure(self) -> str:
        """获取项目结构"""
        try:
            structure = []
            for root, dirs, filenames in os.walk(self.project_path):
                level = root.replace(self.project_path, '').count(os.sep)
                indent = ' ' * 2 * level
                structure.append(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for filename in filenames:
                    structure.append(f"{subindent}{filename}")

            return "\n".join(structure[:20])  # 限制行数
        except:
            return "无法获取项目结构"

    def _get_project_info(self) -> str:
        """获取项目信息"""
        info = [
            f"项目名称: {self.project_name}",
            f"项目路径: {self.project_path}",
            f"需求: {self.context.user_requirements[:200]}...",
            f"架构设计: {self.context.architecture_design[:200]}...",
            f"代码行数: {len(self.context.generated_code.splitlines())}",
            f"测试用例: {len(self.context.test_code.splitlines()) if self.context.test_code else 0}"
        ]
        return "\n".join(info)

    def _get_context_file_path(self) -> str:
        """获取上下文文件路径"""
        context_dir = os.path.join(self.project_path, ".definex_flow")
        os.makedirs(context_dir, exist_ok=True)
        return os.path.join(context_dir, "flow_context.json")

    def _save_context(self):
        """保存上下文到文件"""
        try:
            context_file = self._get_context_file_path()
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(self.context.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存上下文失败: {e}")

    def load_context(self) -> bool:
        """
        从文件加载上下文

        Returns:
            是否成功加载
        """
        try:
            context_file = self._get_context_file_path()
            if os.path.exists(context_file):
                with open(context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.context = FlowContext.from_dict(data)
                    self.is_running = not self.context.completed
                return True
        except Exception as e:
            print(f"加载上下文失败: {e}")

        return False
