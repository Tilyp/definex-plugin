"""
自动化代码生成计划器 - 自动分析需求并生成执行计划
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class TaskType(Enum):
    """任务类型"""
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    INTENT_RECOGNITION = "intent_recognition"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODE_GENERATION = "code_generation"
    TEST_GENERATION = "test_generation"
    TEST_EXECUTION = "test_execution"
    CLEANUP = "cleanup"
    DOCUMENTATION = "documentation"
    FILE_CREATION = "file_creation"
    DEPENDENCY_INSTALL = "dependency_install"
    VALIDATION = "validation"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """任务定义"""
    id: str
    type: TaskType
    title: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    estimated_time: int = 5  # 预估时间（分钟）
    priority: int = 1  # 优先级，1最高

    # 执行相关
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "dependencies": self.dependencies,
            "estimated_time": self.estimated_time,
            "priority": self.priority,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """从字典创建"""
        task = cls(
            id=data["id"],
            type=TaskType(data["type"]),
            title=data["title"],
            description=data["description"],
            dependencies=data.get("dependencies", []),
            estimated_time=data.get("estimated_time", 5),
            priority=data.get("priority", 1)
        )

        task.status = TaskStatus(data.get("status", "pending"))
        task.result = data.get("result")
        task.error = data.get("error")

        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])

        return task


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    project_name: str
    project_path: str
    user_requirements: str

    # 计划数据
    tasks: Dict[str, Task] = field(default_factory=dict)
    task_order: List[str] = field(default_factory=list)

    # 执行状态
    status: str = "created"  # created, planning, executing, completed, failed
    current_task: Optional[str] = None
    progress: float = 0.0

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def add_task(self, task: Task):
        """添加任务"""
        self.tasks[task.id] = task
        if task.id not in self.task_order:
            self.task_order.append(task.id)

    def get_ready_tasks(self) -> List[Task]:
        """获取可以执行的任务（依赖已满足）"""
        ready_tasks = []

        for task_id in self.task_order:
            task = self.tasks[task_id]

            # 跳过已完成或运行中的任务
            if task.status in [TaskStatus.COMPLETED, TaskStatus.RUNNING, TaskStatus.SKIPPED]:
                continue

            # 检查依赖是否满足
            dependencies_met = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    dependencies_met = False
                    break

            if dependencies_met:
                ready_tasks.append(task)

        # 按优先级排序
        ready_tasks.sort(key=lambda t: t.priority)
        return ready_tasks

    def update_progress(self):
        """更新进度"""
        total_tasks = len(self.tasks)
        if total_tasks == 0:
            self.progress = 0.0
            return

        completed_tasks = sum(
            1 for task in self.tasks.values()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        )

        self.progress = (completed_tasks / total_tasks) * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plan_id": self.plan_id,
            "project_name": self.project_name,
            "project_path": self.project_path,
            "user_requirements": self.user_requirements,
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            "task_order": self.task_order,
            "status": self.status,
            "current_task": self.current_task,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        """从字典创建"""
        plan = cls(
            plan_id=data["plan_id"],
            project_name=data["project_name"],
            project_path=data["project_path"],
            user_requirements=data["user_requirements"]
        )

        plan.tasks = {
            task_id: Task.from_dict(task_data)
            for task_id, task_data in data.get("tasks", {}).items()
        }
        plan.task_order = data.get("task_order", [])
        plan.status = data.get("status", "created")
        plan.current_task = data.get("current_task")
        plan.progress = data.get("progress", 0.0)

        plan.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            plan.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            plan.completed_at = datetime.fromisoformat(data["completed_at"])

        return plan


class AutoPlanGenerator:
    """自动化计划生成器"""

    def __init__(self, llm_client=None):
        """
        初始化计划生成器

        Args:
            llm_client: LLM客户端，用于AI分析
        """
        self.llm_client = llm_client

    def generate_plan(self, project_name: str, project_path: str, requirements: str) -> ExecutionPlan:
        """
        生成执行计划

        Args:
            project_name: 项目名称
            project_path: 项目路径
            requirements: 用户需求

        Returns:
            执行计划
        """
        # 生成计划ID
        import uuid
        plan_id = str(uuid.uuid4())[:8]

        # 创建基础计划
        plan = ExecutionPlan(
            plan_id=plan_id,
            project_name=project_name,
            project_path=project_path,
            user_requirements=requirements
        )

        # 分析需求复杂度
        complexity = self._analyze_complexity(requirements)

        # 生成标准任务序列
        self._generate_standard_tasks(plan, complexity)

        # 如果可用，使用LLM优化计划
        if self.llm_client:
            self._optimize_plan_with_llm(plan, requirements)

        # 设置任务顺序
        self._set_task_order(plan)

        plan.status = "planning"
        return plan

    def _analyze_complexity(self, requirements: str) -> str:
        """分析需求复杂度"""
        # 简单启发式分析
        length = len(requirements)
        word_count = len(requirements.split())

        # 检查关键词
        complex_keywords = ["复杂", "高级", "多个", "集成", "系统", "平台", "框架"]
        simple_keywords = ["简单", "基本", "单个", "工具", "插件"]

        complex_count = sum(1 for keyword in complex_keywords if keyword in requirements)
        simple_count = sum(1 for keyword in simple_keywords if keyword in requirements)

        if length > 500 or word_count > 100 or complex_count > simple_count:
            return "high"
        elif length > 200 or word_count > 50:
            return "medium"
        else:
            return "low"

    def _generate_standard_tasks(self, plan: ExecutionPlan, complexity: str):
        """生成标准任务序列"""
        # 基础任务（所有项目都需要）
        base_tasks = [
            Task(
                id="req_analysis",
                type=TaskType.REQUIREMENT_ANALYSIS,
                title="需求分析",
                description="分析用户需求，澄清模糊点，确认功能要求",
                estimated_time=3,
                priority=1
            ),
            Task(
                id="intent_recognition",
                type=TaskType.INTENT_RECOGNITION,
                title="意图识别",
                description="识别用户真实意图和技术水平",
                dependencies=["req_analysis"],
                estimated_time=2,
                priority=2
            ),
            Task(
                id="arch_design",
                type=TaskType.ARCHITECTURE_DESIGN,
                title="架构设计",
                description="设计插件架构，包括类结构和方法设计",
                dependencies=["intent_recognition"],
                estimated_time=5,
                priority=3
            )
        ]

        # 根据复杂度调整代码生成任务
        if complexity == "high":
            code_tasks = [
                Task(
                    id="code_gen_core",
                    type=TaskType.CODE_GENERATION,
                    title="生成核心代码",
                    description="生成插件核心功能代码",
                    dependencies=["arch_design"],
                    estimated_time=10,
                    priority=4
                ),
                Task(
                    id="code_gen_utils",
                    type=TaskType.CODE_GENERATION,
                    title="生成工具类代码",
                    description="生成辅助工具类和函数",
                    dependencies=["code_gen_core"],
                    estimated_time=8,
                    priority=5
                )
            ]
        else:
            code_tasks = [
                Task(
                    id="code_gen",
                    type=TaskType.CODE_GENERATION,
                    title="代码生成",
                    description="生成完整的插件代码",
                    dependencies=["arch_design"],
                    estimated_time=8 if complexity == "medium" else 5,
                    priority=4
                )
            ]

        # 测试任务
        test_tasks = [
            Task(
                id="test_gen",
                type=TaskType.TEST_GENERATION,
                title="测试生成",
                description="为生成的代码编写测试用例",
                dependencies=code_tasks[-1].id,
                estimated_time=6 if complexity == "high" else 4,
                priority=6
            ),
            Task(
                id="test_exec",
                type=TaskType.TEST_EXECUTION,
                title="测试执行",
                description="运行测试并分析结果",
                dependencies=["test_gen"],
                estimated_time=3,
                priority=7
            )
        ]

        # 收尾任务
        final_tasks = [
            Task(
                id="validation",
                type=TaskType.VALIDATION,
                title="代码验证",
                description="验证代码是否符合DefineX规范",
                dependencies=["test_exec"],
                estimated_time=3,
                priority=8
            ),
            Task(
                id="file_creation",
                type=TaskType.FILE_CREATION,
                title="文件创建",
                description="创建项目文件和目录结构",
                dependencies=["validation"],
                estimated_time=2,
                priority=9
            ),
            Task(
                id="documentation",
                type=TaskType.DOCUMENTATION,
                title="文档生成",
                description="生成项目文档和README",
                dependencies=["file_creation"],
                estimated_time=4,
                priority=10
            ),
            Task(
                id="cleanup",
                type=TaskType.CLEANUP,
                title="清理工作",
                description="清理临时文件和测试文件",
                dependencies=["documentation"],
                estimated_time=2,
                priority=11
            )
        ]

        # 添加所有任务到计划
        for task in base_tasks + code_tasks + test_tasks + final_tasks:
            plan.add_task(task)

    def _optimize_plan_with_llm(self, plan: ExecutionPlan, requirements: str):
        """使用LLM优化计划"""
        # 这里可以调用LLM来优化任务分解
        # 暂时使用简单启发式
        pass

    def _set_task_order(self, plan: ExecutionPlan):
        """设置任务执行顺序"""
        # 使用拓扑排序确定任务顺序
        task_ids = list(plan.tasks.keys())

        # 简单的依赖排序
        visited = set()
        order = []

        def dfs(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)

            task = plan.tasks[task_id]
            for dep_id in task.dependencies:
                if dep_id in plan.tasks:
                    dfs(dep_id)

            order.append(task_id)

        for task_id in task_ids:
            if task_id not in visited:
                dfs(task_id)

        plan.task_order = order
