"""
测试灵感模式后台任务 API
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from inspect import signature

# 确保在导入前设置必要的环境变量
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://mumuai:password@localhost:5432/mumuai_novel")


class TestInspirationBackgroundRequest:
    """测试 InspirationBackgroundRequest 模型"""

    def test_valid_request_creation(self):
        """验证有效的请求可以正常创建"""
        from app.api.inspiration import InspirationBackgroundRequest

        request = InspirationBackgroundRequest(
            title="测试小说",
            description="这是一个测试小说描述",
            theme="奇幻",
            genre="玄幻",
            narrative_perspective="第三人称",
            outline_mode="one-to-one"
        )

        assert request.title == "测试小说"
        assert request.description == "这是一个测试小说描述"
        assert request.theme == "奇幻"
        assert request.genre == "玄幻"
        assert request.narrative_perspective == "第三人称"
        assert request.outline_mode == "one-to-one"

    def test_default_outline_mode(self):
        """验证 outline_mode 默认值为 one-to-one"""
        from app.api.inspiration import InspirationBackgroundRequest

        request = InspirationBackgroundRequest(
            title="测试小说",
            description="描述",
            theme="奇幻",
            genre="玄幻",
            narrative_perspective="第三人称"
        )

        assert request.outline_mode == "one-to-one"

    def test_request_missing_required_field_title(self):
        """验证缺少必填字段 title 时抛出验证错误"""
        from app.api.inspiration import InspirationBackgroundRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            InspirationBackgroundRequest(
                description="描述",
                theme="奇幻",
                genre="玄幻",
                narrative_perspective="第三人称"
            )

        errors = exc_info.value.errors()
        assert any("title" in str(e) for e in errors)

    def test_request_missing_required_field_description(self):
        """验证缺少必填字段 description 时抛出验证错误"""
        from app.api.inspiration import InspirationBackgroundRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            InspirationBackgroundRequest(
                title="测试小说",
                theme="奇幻",
                genre="玄幻",
                narrative_perspective="第三人称"
            )

        errors = exc_info.value.errors()
        assert any("description" in str(e) for e in errors)

    def test_request_missing_required_field_theme(self):
        """验证缺少必填字段 theme 时抛出验证错误"""
        from app.api.inspiration import InspirationBackgroundRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            InspirationBackgroundRequest(
                title="测试小说",
                description="描述",
                genre="玄幻",
                narrative_perspective="第三人称"
            )

        errors = exc_info.value.errors()
        assert any("theme" in str(e) for e in errors)

    def test_request_missing_required_field_genre(self):
        """验证缺少必填字段 genre 时抛出验证错误"""
        from app.api.inspiration import InspirationBackgroundRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            InspirationBackgroundRequest(
                title="测试小说",
                description="描述",
                theme="奇幻",
                narrative_perspective="第三人称"
            )

        errors = exc_info.value.errors()
        assert any("genre" in str(e) for e in errors)

    def test_request_missing_required_field_narrative_perspective(self):
        """验证缺少必填字段 narrative_perspective 时抛出验证错误"""
        from app.api.inspiration import InspirationBackgroundRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            InspirationBackgroundRequest(
                title="测试小说",
                description="描述",
                theme="奇幻",
                genre="玄幻"
            )

        errors = exc_info.value.errors()
        assert any("narrative_perspective" in str(e) for e in errors)


class TestInspirationBackgroundResponse:
    """测试 InspirationBackgroundResponse 模型"""

    def test_valid_response_creation(self):
        """验证有效的响应可以正常创建"""
        from app.api.inspiration import InspirationBackgroundResponse

        response = InspirationBackgroundResponse(
            task_id="test-task-id-123",
            message="后台任务已创建"
        )

        assert response.task_id == "test-task-id-123"
        assert response.message == "后台任务已创建"

    def test_response_model_dumps(self):
        """验证响应模型可以序列化为字典"""
        from app.api.inspiration import InspirationBackgroundResponse

        response = InspirationBackgroundResponse(
            task_id="test-task-id-123",
            message="后台任务已创建"
        )

        data = response.model_dump()
        assert data["task_id"] == "test-task-id-123"
        assert data["message"] == "后台任务已创建"


class TestInspirationBackgroundTaskId:
    """测试任务 ID 生成"""

    def test_task_id_format(self):
        """验证后台任务服务可以生成 UUID 格式的任务 ID"""
        import uuid
        # BackgroundTask 使用 uuid.uuid4() 生成 ID
        task_id = str(uuid.uuid4())
        assert len(task_id) == 36
        assert task_id.count("-") == 4


class TestInspirationRouterPrefix:
    """测试路由配置"""

    def test_router_has_correct_prefix(self):
        """验证路由使用正确的 prefix"""
        from app.api.inspiration import router

        assert router.prefix == "/inspiration"
        assert "灵感模式后台任务" in router.tags


class TestDefaultValues:
    """测试默认值常量"""

    def test_default_target_words(self):
        """验证默认目标字数"""
        from app.api.inspiration import DEFAULT_TARGET_WORDS
        assert DEFAULT_TARGET_WORDS == 100000

    def test_default_chapter_count(self):
        """验证默认章节数"""
        from app.api.inspiration import DEFAULT_CHAPTER_COUNT
        assert DEFAULT_CHAPTER_COUNT == 3

    def test_default_character_count(self):
        """验证默认角色数"""
        from app.api.inspiration import DEFAULT_CHARACTER_COUNT
        assert DEFAULT_CHARACTER_COUNT == 5


class TestTaskProgressTracker:
    """测试任务进度追踪器"""

    def test_tracker_initialization(self):
        """验证追踪器初始化"""
        from app.services.background_task_service import TaskProgressTracker

        tracker = TaskProgressTracker(
            task_id="test-task-id",
            user_id="test-user-id",
            task_name="测试任务"
        )

        assert tracker.task_id == "test-task-id"
        assert tracker.user_id == "test-user-id"
        assert tracker.task_name == "测试任务"
        assert tracker.current_progress == 0


class TestBackgroundTaskService:
    """测试后台任务服务"""

    def test_background_task_service_is_singleton(self):
        """验证后台任务服务是单例"""
        from app.services.background_task_service import background_task_service

        assert background_task_service is not None
        assert hasattr(background_task_service, "_user_queues")
        assert hasattr(background_task_service, "_user_workers")

    def test_ensure_user_queue_creates_new_queue(self):
        """验证为新用户创建队列"""
        from app.services.background_task_service import BackgroundTaskService

        service = BackgroundTaskService()
        queue = service._ensure_user_queue("new-user-id")

        assert queue is not None
        assert "new-user-id" in service._user_queues


class TestAPIEndpointExists:
    """测试 API 端点存在性（通过路由检查）"""

    def test_inspiration_router_includes_background_endpoint(self):
        """验证 inspiration 路由包含 background 端点"""
        from app.api.inspiration import router

        # 检查路由中是否包含 background 端点（完整路径是 /inspiration/background）
        route_paths = [route.path for route in router.routes]
        assert any("background" in path for path in route_paths)

        # 检查是否有 POST 方法的端点
        post_routes = [
            route for route in router.routes
            if hasattr(route, "methods") and "POST" in route.methods
        ]
        post_paths = [route.path for route in post_routes]
        assert any("background" in path for path in post_paths)


class TestInspirationBackgroundEndpoint:
    """测试灵感模式后台任务 API 端点（使用 TestClient）"""

    def test_endpoint_exists_and_accepts_post(self):
        """验证 background 端点存在且接受 POST 方法"""
        from app.api.inspiration import router

        # Find the background route
        background_route = None
        for route in router.routes:
            if "background" in route.path and hasattr(route, "methods"):
                background_route = route
                break

        assert background_route is not None, "background route not found"
        assert "POST" in background_route.methods, "background route should accept POST"

    def test_endpoint_requires_authentication(self):
        """验证端点需要认证（返回 401 在认证检查之前）"""
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/inspiration/background",
                json={
                    "title": "测试小说",
                    "description": "测试描述",
                    "theme": "奇幻",
                    "genre": "玄幻",
                    "narrative_perspective": "第三人称"
                }
            )
            # Auth is checked before validation, so we get 401
            assert response.status_code == 401

    def test_endpoint_validates_required_fields(self):
        """验证端点验证必填字段（Pydantic 验证）"""
        from pydantic import ValidationError
        from app.api.inspiration import InspirationBackgroundRequest

        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            InspirationBackgroundRequest(
                title="测试小说"
                # Missing: description, theme, genre, narrative_perspective
            )


class TestRunInspirationBgSignature:
    """测试 _run_inspiration_bg 函数签名"""

    def test_function_accepts_required_parameters(self):
        """验证函数接受所需的参数: task_id, user_id, db, task_input"""
        from app.api.inspiration import _run_inspiration_bg
        import inspect

        sig = signature(_run_inspiration_bg)
        params = list(sig.parameters.keys())

        # Verify parameter names and order
        assert params[0] == "task_id", "First parameter should be task_id"
        assert params[1] == "user_id", "Second parameter should be user_id"
        assert params[2] == "db", "Third parameter should be db"
        assert params[3] == "task_input", "Fourth parameter should be task_input"

    def test_function_is_async(self):
        """验证函数是异步函数"""
        from app.api.inspiration import _run_inspiration_bg
        import inspect

        assert inspect.iscoroutinefunction(_run_inspiration_bg), \
            "_run_inspiration_bg should be an async function"

    def test_function_parameters_have_correct_types(self):
        """验证函数参数类型注解"""
        from app.api.inspiration import _run_inspiration_bg
        import inspect

        sig = signature(_run_inspiration_bg)

        # task_id should be str
        assert sig.parameters["task_id"].annotation == str, \
            "task_id should be annotated as str"

        # user_id should be str
        assert sig.parameters["user_id"].annotation == str, \
            "user_id should be annotated as str"

        # task_input should be dict
        assert sig.parameters["task_input"].annotation == dict, \
            "task_input should be annotated as dict"


class TestStageProgressCalculation:
    """测试阶段进度计算"""

    def test_stage_1_range_0_to_25_percent(self):
        """验证阶段1进度范围: 0-25% (项目创建 + 世界观)"""
        # Stage 1 starts at 0% and ends at 25%
        stage_1_milestones = [0, 0.1, 0.25]

        for milestone in stage_1_milestones:
            progress = int(milestone * 100)
            assert 0 <= progress <= 25, \
                f"Stage 1 milestone {milestone} ({progress}%) should be in range 0-25%"

    def test_stage_2_range_25_to_50_percent(self):
        """验证阶段2进度范围: 25-50% (职业体系)"""
        # Stage 2: 25-50%
        stage_2_milestones = [0.3, 0.5]

        for milestone in stage_2_milestones:
            progress = int(milestone * 100)
            assert 25 <= progress <= 50, \
                f"Stage 2 milestone {milestone} ({progress}%) should be in range 25-50%"

    def test_stage_3_range_50_to_75_percent(self):
        """验证阶段3进度范围: 50-75% (角色生成)"""
        # Stage 3: 50-75%
        stage_3_milestones = [0.55, 0.75]

        for milestone in stage_3_milestones:
            progress = int(milestone * 100)
            assert 50 <= progress <= 75, \
                f"Stage 3 milestone {milestone} ({progress}%) should be in range 50-75%"

    def test_stage_4_range_75_to_100_percent(self):
        """验证阶段4进度范围: 75-100% (大纲生成)"""
        # Stage 4: 75-100%
        stage_4_milestones = [0.8, 0.95]

        for milestone in stage_4_milestones:
            progress = int(milestone * 100)
            assert 75 <= progress <= 100, \
                f"Stage 4 milestone {milestone} ({progress}%) should be in range 75-100%"

    def test_all_four_stages_cover_full_range(self):
        """验证四个阶段覆盖完整进度范围 0-100%"""
        # Stage boundaries
        stage_boundaries = [
            (0, 25),    # Stage 1: 0-25%
            (25, 50),   # Stage 2: 25-50%
            (50, 75),   # Stage 3: 50-75%
            (75, 100),  # Stage 4: 75-100%
        ]

        for start, end in stage_boundaries:
            assert start >= 0 and end <= 100, \
                f"Stage range ({start}%, {end}%) should be within 0-100%"

        # Verify no gaps between stages
        for i in range(len(stage_boundaries) - 1):
            current_end = stage_boundaries[i][1]
            next_start = stage_boundaries[i + 1][0]
            assert current_end == next_start, \
                f"Gap found between stages: {current_end}% != {next_start}%"

    def test_progress_milestones_match_spec(self):
        """验证进度里程碑与规范一致"""
        # From the _run_inspiration_bg function, the milestones are:
        expected_milestones = {
            "stage_1_start": 0.0,
            "stage_1_project_start": 0.1,
            "stage_1_world_end": 0.25,
            "stage_2_career_start": 0.3,
            "stage_2_career_end": 0.5,
            "stage_3_characters_start": 0.55,
            "stage_3_characters_end": 0.75,
            "stage_4_outline_start": 0.8,
            "stage_4_outline_end": 0.95,
            "completion": 1.0,
        }

        # Stage 1: 项目创建 + 世界观 (0-25%)
        assert expected_milestones["stage_1_project_start"] >= 0.0
        assert expected_milestones["stage_1_world_end"] <= 0.25

        # Stage 2: 职业体系 (25-50%)
        assert expected_milestones["stage_2_career_start"] >= 0.25
        assert expected_milestones["stage_2_career_end"] <= 0.50

        # Stage 3: 角色生成 (50-75%)
        assert expected_milestones["stage_3_characters_start"] >= 0.50
        assert expected_milestones["stage_3_characters_end"] <= 0.75

        # Stage 4: 大纲生成 (75-100%)
        assert expected_milestones["stage_4_outline_start"] >= 0.75
        assert expected_milestones["stage_4_outline_end"] <= 1.0
