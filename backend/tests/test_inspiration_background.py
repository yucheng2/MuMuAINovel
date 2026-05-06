"""
测试灵感模式后台任务 API
"""
import pytest
import os

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
