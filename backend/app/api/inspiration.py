"""灵感模式API - 通过对话引导创建项目"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

from app.database import get_db
from app.services.ai_service import AIService
from app.services.json_helper import loads_json
from app.api.settings import get_user_ai_service, get_user_ai_service_from_db
from app.services.prompt_service import PromptService
from app.services.background_task_service import (
    TaskProgressTracker,
    BackgroundTaskService,
    background_task_service,
)
from app.logger import get_logger

router = APIRouter(prefix="/inspiration", tags=["灵感模式"])
logger = get_logger(__name__)

# Default values for inspiration mode
DEFAULT_TARGET_WORDS = 100000
DEFAULT_CHAPTER_COUNT = 3
DEFAULT_CHARACTER_COUNT = 5


# 不同阶段的temperature设置（递减以保持一致性）
TEMPERATURE_SETTINGS = {
    "title": 0.8,        # 书名阶段可以更有创意
    "description": 0.65, # 简介需要贴合书名和原始想法
    "theme": 0.55,       # 主题需要更加贴合
    "genre": 0.45        # 类型应该很明确
}


def validate_options_response(result: Dict[str, Any], step: str, max_retries: int = 3) -> tuple[bool, str]:
    """
    校验AI返回的选项格式是否正确
    
    Returns:
        (is_valid, error_message)
    """
    # 检查必需字段
    if "options" not in result:
        return False, "缺少options字段"
    
    options = result.get("options", [])
    
    # 检查options是否为数组
    if not isinstance(options, list):
        return False, "options必须是数组"
    
    # 检查数组长度
    if len(options) < 3:
        return False, f"选项数量不足，至少需要3个，当前只有{len(options)}个"
    
    if len(options) > 10:
        return False, f"选项数量过多，最多10个，当前有{len(options)}个"
    
    # 检查每个选项是否为字符串且不为空
    for i, option in enumerate(options):
        if not isinstance(option, str):
            return False, f"第{i+1}个选项不是字符串类型"
        if not option.strip():
            return False, f"第{i+1}个选项为空"
        if len(option) > 500:
            return False, f"第{i+1}个选项过长（超过500字符）"
    
    # 根据不同步骤进行特定校验
    if step == "genre":
        # 类型标签应该比较短
        for i, option in enumerate(options):
            if len(option) > 10:
                return False, f"类型标签【{option}】过长，应该在2-10字之间"
    
    return True, ""


@router.post("/generate-options")
async def generate_options(
    data: Dict[str, Any],
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    ai_service: AIService = Depends(get_user_ai_service)
) -> Dict[str, Any]:
    """
    根据当前收集的信息生成下一步的选项建议（带自动重试）
    
    Request:
        {
            "step": "title",  // title/description/theme/genre
            "context": {
                "title": "...",
                "description": "...",
                "theme": "..."
            }
        }
    
    Response:
        {
            "prompt": "引导语",
            "options": ["选项1", "选项2", ...]
        }
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            step = data.get("step", "title")
            context = data.get("context", {})
            
            logger.info(f"灵感模式：生成{step}阶段的选项（第{attempt + 1}次尝试）")
            
            # 获取用户ID
            user_id = getattr(http_request.state, 'user_id', None)
            
            # 获取对应的提示词模板（根据step确定模板key）
            # 新结构：每个步骤有独立的 SYSTEM 和 USER 模板
            template_key_map = {
                "title": ("INSPIRATION_TITLE_SYSTEM", "INSPIRATION_TITLE_USER"),
                "description": ("INSPIRATION_DESCRIPTION_SYSTEM", "INSPIRATION_DESCRIPTION_USER"),
                "theme": ("INSPIRATION_THEME_SYSTEM", "INSPIRATION_THEME_USER"),
                "genre": ("INSPIRATION_GENRE_SYSTEM", "INSPIRATION_GENRE_USER")
            }
            template_keys = template_key_map.get(step)
            
            if not template_keys:
                return {
                    "error": f"不支持的步骤: {step}",
                    "prompt": "",
                    "options": []
                }
            
            system_key, user_key = template_keys
            
            # 获取自定义提示词模板（分别获取 system 和 user）
            system_template = await PromptService.get_template(system_key, user_id, db)
            user_template = await PromptService.get_template(user_key, user_id, db)
            
            # 准备格式化参数
            format_params = {
                "initial_idea": context.get("initial_idea", context.get("description", "")),
                "title": context.get("title", ""),
                "description": context.get("description", ""),
                "theme": context.get("theme", "")
            }
            
            # 格式化提示词
            system_prompt = system_template.format(**format_params)
            user_prompt = user_template.format(**format_params)
            
            # 如果是重试，在提示词中强调格式要求
            if attempt > 0:
                system_prompt += f"\n\n⚠️ 这是第{attempt + 1}次生成，请务必严格按照JSON格式返回，确保options数组包含6个有效选项！"
            
            # 调用AI生成选项
            # 关键改进：使用递减的temperature以保持后续阶段与前文的一致性
            temperature = TEMPERATURE_SETTINGS.get(step, 0.7)
            logger.info(f"调用AI生成{step}选项... (temperature={temperature})")
            
            # 流式生成并累积文本
            accumulated_text = ""
            async for chunk in ai_service.generate_text_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature
            ):
                accumulated_text += chunk
            
            response = {"content": accumulated_text}
            content = accumulated_text
            logger.info(f"AI返回内容长度: {len(content)}")
            
            # 解析JSON（使用统一的JSON清洗方法）
            try:
                # 使用统一的JSON清洗方法
                cleaned_content = ai_service._clean_json_response(content)
                
                result = loads_json(cleaned_content)
                
                # 校验返回格式
                is_valid, error_msg = validate_options_response(result, step)
                
                if not is_valid:
                    logger.warning(f"⚠️ 第{attempt + 1}次生成格式校验失败: {error_msg}")
                    if attempt < max_retries - 1:
                        logger.info("准备重试...")
                        continue  # 重试
                    else:
                        # 最后一次尝试也失败了
                        return {
                            "prompt": f"请为【{step}】提供内容：",
                            "options": ["让AI重新生成", "我自己输入"],
                            "error": f"AI生成格式错误（{error_msg}），已自动重试{max_retries}次，请手动重试或自己输入"
                        }
                
                logger.info(f"✅ 第{attempt + 1}次成功生成{len(result.get('options', []))}个有效选项")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"第{attempt + 1}次JSON解析失败: {e}")
                
                if attempt < max_retries - 1:
                    logger.info("JSON解析失败，准备重试...")
                    continue  # 重试
                else:
                    # 最后一次尝试也失败了
                    return {
                        "prompt": f"请为【{step}】提供内容：",
                        "options": ["让AI重新生成", "我自己输入"],
                        "error": f"AI返回格式错误，已自动重试{max_retries}次，请手动重试或自己输入"
                    }
        
        except Exception as e:
            logger.error(f"第{attempt + 1}次生成失败: {e}", exc_info=True)
            if attempt < max_retries - 1:
                logger.info("发生异常，准备重试...")
                continue
            else:
                return {
                    "error": str(e),
                    "prompt": "生成失败，请重试",
                    "options": ["重新生成", "我自己输入"]
                }
    
    # 理论上不会到这里
    return {
        "error": "生成失败",
        "prompt": "请重试",
        "options": []
    }


@router.post("/refine-options")
async def refine_options(
    data: Dict[str, Any],
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    ai_service: AIService = Depends(get_user_ai_service)
) -> Dict[str, Any]:
    """
    基于用户反馈重新生成选项（支持多轮对话）
    
    Request:
        {
            "step": "title",  // 当前步骤
            "context": {
                "initial_idea": "...",
                "title": "...",
                "description": "...",
                "theme": "..."
            },
            "feedback": "我想要更悲剧一些的主题",  // 用户反馈
            "previous_options": ["选项1", "选项2", ...]  // 之前的选项（可选）
        }
    
    Response:
        {
            "prompt": "引导语",
            "options": ["新选项1", "新选项2", ...]
        }
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            step = data.get("step", "title")
            context = data.get("context", {})
            feedback = data.get("feedback", "")
            previous_options = data.get("previous_options", [])
            
            logger.info(f"灵感模式：根据反馈重新生成{step}阶段的选项（第{attempt + 1}次尝试）")
            logger.info(f"用户反馈: {feedback}")
            
            # 获取用户ID
            user_id = getattr(http_request.state, 'user_id', None)
            
            # 获取对应的提示词模板
            template_key_map = {
                "title": ("INSPIRATION_TITLE_SYSTEM", "INSPIRATION_TITLE_USER"),
                "description": ("INSPIRATION_DESCRIPTION_SYSTEM", "INSPIRATION_DESCRIPTION_USER"),
                "theme": ("INSPIRATION_THEME_SYSTEM", "INSPIRATION_THEME_USER"),
                "genre": ("INSPIRATION_GENRE_SYSTEM", "INSPIRATION_GENRE_USER")
            }
            template_keys = template_key_map.get(step)
            
            if not template_keys:
                return {
                    "error": f"不支持的步骤: {step}",
                    "prompt": "",
                    "options": []
                }
            
            system_key, user_key = template_keys
            
            # 获取自定义提示词模板
            system_template = await PromptService.get_template(system_key, user_id, db)
            user_template = await PromptService.get_template(user_key, user_id, db)
            
            # 准备格式化参数
            format_params = {
                "initial_idea": context.get("initial_idea", context.get("description", "")),
                "title": context.get("title", ""),
                "description": context.get("description", ""),
                "theme": context.get("theme", "")
            }
            
            # 格式化提示词
            system_prompt = system_template.format(**format_params)
            user_prompt = user_template.format(**format_params)
            
            # 添加反馈信息到提示词
            feedback_instruction = f"""

⚠️ 用户对之前的选项不太满意，提供了以下反馈：
「{feedback}」

之前生成的选项：
{chr(10).join([f"- {opt}" for opt in previous_options]) if previous_options else "（无）"}

请根据用户的反馈调整生成策略，提供更符合用户期望的新选项。
注意：
1. 仔细理解用户的反馈意图
2. 生成的新选项要明显体现用户要求的调整方向
3. 保持与已有上下文的一致性
4. 确保返回6个有效选项
"""
            
            system_prompt += feedback_instruction
            
            # 如果是重试，强调格式要求
            if attempt > 0:
                system_prompt += f"\n\n⚠️ 这是第{attempt + 1}次生成，请务必严格按照JSON格式返回！"
            
            # 调用AI生成选项
            temperature = TEMPERATURE_SETTINGS.get(step, 0.7)
            # 反馈生成时使用稍高的temperature以获得更多样化的结果
            temperature = min(temperature + 0.1, 0.9)
            logger.info(f"调用AI根据反馈生成{step}选项... (temperature={temperature})")
            
            # 流式生成并累积文本
            accumulated_text = ""
            async for chunk in ai_service.generate_text_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature
            ):
                accumulated_text += chunk
            
            content = accumulated_text
            logger.info(f"AI返回内容长度: {len(content)}")
            
            # 解析JSON
            try:
                cleaned_content = ai_service._clean_json_response(content)
                result = loads_json(cleaned_content)
                
                # 校验返回格式
                is_valid, error_msg = validate_options_response(result, step)
                
                if not is_valid:
                    logger.warning(f"⚠️ 第{attempt + 1}次生成格式校验失败: {error_msg}")
                    if attempt < max_retries - 1:
                        logger.info("准备重试...")
                        continue
                    else:
                        return {
                            "prompt": f"请为【{step}】提供内容：",
                            "options": ["让AI重新生成", "我自己输入"],
                            "error": f"AI生成格式错误（{error_msg}），已自动重试{max_retries}次"
                        }
                
                logger.info(f"✅ 第{attempt + 1}次根据反馈成功生成{len(result.get('options', []))}个有效选项")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"第{attempt + 1}次JSON解析失败: {e}")
                
                if attempt < max_retries - 1:
                    logger.info("JSON解析失败，准备重试...")
                    continue
                else:
                    return {
                        "prompt": f"请为【{step}】提供内容：",
                        "options": ["让AI重新生成", "我自己输入"],
                        "error": f"AI返回格式错误，已自动重试{max_retries}次"
                    }
        
        except Exception as e:
            logger.error(f"第{attempt + 1}次根据反馈生成失败: {e}", exc_info=True)
            if attempt < max_retries - 1:
                logger.info("发生异常，准备重试...")
                continue
            else:
                return {
                    "error": str(e),
                    "prompt": "生成失败，请重试",
                    "options": ["重新生成", "我自己输入"]
                }
    
    return {
        "error": "生成失败",
        "prompt": "请重试",
        "options": []
    }


@router.post("/quick-generate")
async def quick_generate(
    data: Dict[str, Any],
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    ai_service: AIService = Depends(get_user_ai_service)
) -> Dict[str, Any]:
    """
    智能补全：根据用户已提供的部分信息，AI自动补全缺失字段
    
    Request:
        {
            "title": "书名（可选）",
            "description": "简介（可选）",
            "theme": "主题（可选）",
            "genre": ["类型1", "类型2"]（可选）
        }
    
    Response:
        {
            "title": "补全的书名",
            "description": "补全的简介",
            "theme": "补全的主题",
            "genre": ["补全的类型"]
        }
    """
    try:
        logger.info("灵感模式：智能补全")
        
        # 获取用户ID
        user_id = getattr(http_request.state, 'user_id', None)
        
        # 构建补全提示词
        existing_info = []
        if data.get("title"):
            existing_info.append(f"- 书名：{data['title']}")
        if data.get("description"):
            existing_info.append(f"- 简介：{data['description']}")
        if data.get("theme"):
            existing_info.append(f"- 主题：{data['theme']}")
        if data.get("genre"):
            existing_info.append(f"- 类型：{', '.join(data['genre'])}")
        
        existing_text = "\n".join(existing_info) if existing_info else "暂无信息"
        
        # 获取自定义提示词模板
        system_template = await PromptService.get_template("INSPIRATION_QUICK_COMPLETE", user_id, db)
        
        # 格式化提示词
        prompts = {
            "system": PromptService.format_prompt(system_template, existing=existing_text),
            "user": "请补全小说信息"
        }
        
        # 调用AI - 流式生成并累积文本
        accumulated_text = ""
        async for chunk in ai_service.generate_text_stream(
            prompt=prompts["user"],
            system_prompt=prompts["system"],
            temperature=0.7
        ):
            accumulated_text += chunk
        
        response = {"content": accumulated_text}
        content = accumulated_text
        
        # 解析JSON（使用统一的JSON清洗方法）
        try:
            # 使用统一的JSON清洗方法
            cleaned_content = ai_service._clean_json_response(content)
            
            result = loads_json(cleaned_content)
            
            # 合并用户已提供的信息（用户输入优先）
            final_result = {
                "title": data.get("title") or result.get("title", ""),
                "description": data.get("description") or result.get("description", ""),
                "theme": data.get("theme") or result.get("theme", ""),
                "genre": data.get("genre") or result.get("genre", [])
            }
            
            logger.info(f"✅ 智能补全成功")
            return final_result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise Exception("AI返回格式错误，请重试")
    
    except Exception as e:
        logger.error(f"智能补全失败: {e}", exc_info=True)
        return {
            "error": str(e)
        }


# ==================== 后台任务相关 ====================

class InspirationBackgroundRequest(BaseModel):
    title: str
    description: str
    theme: str
    genre: str  # 前端发送的是genre标签字符串或数组
    narrative_perspective: str
    outline_mode: str = "one-to-one"


class InspirationBackgroundResponse(BaseModel):
    task_id: str
    message: str


async def _run_inspiration_bg(task_id: str, user_id: str, task_input: dict):
    """后台执行灵感模式创建任务"""
    import asyncio
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.database import get_engine

    title = task_input.get("title", "未命名")
    task_name = f"《{title}》创建中"
    tracker = TaskProgressTracker(task_id, user_id, task_name)

    async def send_heartbeat(msg: str = None):
        """发送心跳，防止任务被误判为超时"""
        await tracker.heartbeat(msg or "心跳中...")

    try:
        # 创建独立的数据库会话
        engine = await get_engine(user_id)
        AsyncSessionLocal = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # 导入 wizard_stream 服务
        from app.services.wizard_stream_service import WizardStreamService
        from app.api.settings import get_user_ai_service_from_db

        async with AsyncSessionLocal() as db:
            # 获取用户AI服务实例
            user_ai_service = await get_user_ai_service_from_db(user_id, db)
            service = WizardStreamService(db, user_ai_service)

            # 阶段1: 项目创建 + 世界观 (0-25%)
            await tracker.start(f"《{title}》创建中...")

            # 检查是否已有 project_id（重试时）
            existing_project_id = task_input.get("project_id")
            if existing_project_id:
                project_id = existing_project_id
                await tracker.loading(f"《{title}》已存在，跳过项目创建...", 0.1)
                await send_heartbeat(f"《{title}》跳过项目创建...")
            else:
                await tracker.loading("创建项目中...", 0.1)
                await send_heartbeat(f"《{title}》创建中...")

                world_result = await service.generate_world_building({
                    "user_id": user_id,
                    "title": title,
                    "description": task_input.get("description", ""),
                    "theme": task_input.get("theme", ""),
                    "genre": task_input.get("genre", "都市"),
                    "narrative_perspective": task_input.get("narrative_perspective", "第一人称"),
                    "target_words": DEFAULT_TARGET_WORDS,
                    "chapter_count": DEFAULT_CHAPTER_COUNT,
                    "character_count": DEFAULT_CHARACTER_COUNT,
                    "outline_mode": task_input.get("outline_mode", "one-to-one"),
                })
                project_id = world_result["project_id"]

            # 保存 project_id 到 task_input，以便重试时使用
            from sqlalchemy import update
            from app.models.background_task import BackgroundTask
            await db.execute(
                update(BackgroundTask)
                .where(BackgroundTask.id == task_id)
                .values(task_input={**task_input, "project_id": project_id})
            )
            await db.commit()

            await tracker.loading(f"《{title}》世界观生成完成", 0.25)
            await send_heartbeat(f"《{title}》世界观生成完成")

            # 阶段2: 职业体系 (25-50%)
            await tracker.loading("生成职业体系中...", 0.3)
            await send_heartbeat("生成职业体系中...")
            await service.generate_career_system({
                "project_id": project_id,
                "user_id": user_id,
            })
            await tracker.loading(f"《{title}》职业体系生成完成", 0.5)
            await send_heartbeat(f"《{title}》职业体系生成完成")

            # 阶段3: 角色生成 (50-75%)
            await tracker.loading("生成角色中...", 0.55)
            await send_heartbeat("生成角色中...")
            await service.generate_characters({
                "project_id": project_id,
                "user_id": user_id,
                "count": DEFAULT_CHARACTER_COUNT,
            })
            await tracker.loading(f"《{title}》角色生成完成", 0.75)
            await send_heartbeat(f"《{title}》角色生成完成")

            # 阶段4: 大纲生成 (75-100%)
            await tracker.loading("生成大纲中...", 0.8)
            await send_heartbeat("生成大纲中...")
            await service.generate_outline({
                "project_id": project_id,
                "user_id": user_id,
                "chapter_count": DEFAULT_CHAPTER_COUNT,
                "narrative_perspective": task_input.get("narrative_perspective", "第一人称"),
                "target_words": DEFAULT_TARGET_WORDS,
            })
            await tracker.loading(f"《{title}》大纲生成完成", 0.95)

            await tracker.complete(f"《{title}》创建成功！")

    except Exception as e:
        logger.error(f"灵感模式后台任务失败: {e}")
        await tracker.error(str(e))
        raise


async def _run_inspiration_auto_bg(task_id: str, user_id: str, task_input: dict):
    """后台执行一键灵感模式：AI生成所有答案后创建项目"""
    import asyncio
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.database import get_engine

    initial_idea = task_input.get("initial_idea", "")
    task_name = "灵感后台创建中"
    tracker = TaskProgressTracker(task_id, user_id, task_name)

    async def send_heartbeat(msg: str = None):
        await tracker.heartbeat(msg or "心跳中...")

    try:
        # 创建独立的数据库会话
        engine = await get_engine(user_id)
        AsyncSessionLocal = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # 导入必要的服务
        from app.services.wizard_stream_service import WizardStreamService
        from app.api.settings import get_user_ai_service_from_db

        async with AsyncSessionLocal() as db:
            # 获取用户AI服务实例
            ai_service = await get_user_ai_service_from_db(user_id, db)

            context = {
                "initial_idea": initial_idea,
                "title": "",
                "description": "",
                "theme": ""
            }

            # 阶段0: AI生成标题 (0-10%)
            await tracker.start("灵感后台创建中...")
            await tracker.loading("AI生成标题中...", 0.02)
            await send_heartbeat("AI生成标题中...")
            try:
                title = await _generate_single_option("title", context, user_id, db, ai_service)
                context["title"] = title
            except Exception as e:
                logger.error(f"标题生成失败: {e}")
                raise Exception(f"标题生成失败: {str(e)}")

            # 阶段0: AI生成简介 (10-20%)
            await tracker.loading(f"《{title}》AI生成简介中...", 0.05)
            await send_heartbeat("AI生成简介中...")
            try:
                description = await _generate_single_option("description", context, user_id, db, ai_service)
                context["description"] = description
            except Exception as e:
                logger.error(f"简介生成失败: {e}")
                raise Exception(f"简介生成失败: {str(e)}")

            # 阶段0: AI生成主题 (20-30%)
            await tracker.loading(f"《{title}》AI生成主题中...", 0.08)
            await send_heartbeat("AI生成主题中...")
            try:
                theme = await _generate_single_option("theme", context, user_id, db, ai_service)
                context["theme"] = theme
            except Exception as e:
                logger.error(f"主题生成失败: {e}")
                raise Exception(f"主题生成失败: {str(e)}")

            # 阶段0: AI生成类型 (30-40%) - 多选标签
            await tracker.loading(f"《{title}》AI生成类型中...", 0.12)
            await send_heartbeat("AI生成类型中...")
            try:
                genre_list = await _generate_genre_options(context, user_id, db, ai_service)
                # 取前3个标签作为默认选中
                genre = genre_list[:3] if len(genre_list) >= 3 else genre_list
            except Exception as e:
                logger.error(f"类型生成失败: {e}")
                genre = ["都市"]  # 默认类型

            # 将 genre 数组转为逗号分隔的字符串
            genre_str = ", ".join(genre) if isinstance(genre, list) else genre

            logger.info(f"AI生成完成: title={title}, description={description}, theme={theme}, genre={genre_str}")

            # 构建完整的 task_input 传递给 _run_inspiration_bg
            final_task_input = {
                "title": title,
                "description": description,
                "theme": theme,
                "genre": genre_str,  # 转为字符串
                "narrative_perspective": "第一人称",
                "outline_mode": "one-to-one",
                "user_id": user_id,
            }

            # 将完整的 task_input 更新到数据库，以便重试时使用
            from sqlalchemy import update
            from app.models.background_task import BackgroundTask
            await db.execute(
                update(BackgroundTask)
                .where(BackgroundTask.id == task_id)
                .values(task_input=final_task_input)
            )
            await db.commit()

        # 关闭当前 db session，调用 _run_inspiration_bg（它会创建自己的 session）
        await tracker.loading(f"《{title}》开始创建项目...", 0.15)
        await send_heartbeat(f"《{title}》开始创建项目...")

        # 调用现有的 _run_inspiration_bg 执行项目创建
        await _run_inspiration_bg(task_id, user_id, final_task_input)

    except Exception as e:
        logger.error(f"灵感后台自动创建任务失败: {e}")
        await tracker.error(str(e))
        raise


@router.post("/background", response_model=InspirationBackgroundResponse)
async def create_inspiration_background_task(
    data: InspirationBackgroundRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """创建灵感模式后台任务"""
    # 从认证中间件获取用户ID
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要登录")

    task = await BackgroundTaskService.create_task(
        user_id=user_id,
        project_id=None,
        task_type="inspiration",
        task_input=data.model_dump(),
        db=db,
    )

    task_input = data.model_dump()
    task_input["user_id"] = user_id

    await background_task_service.spawn_background_task(
        task.id,
        user_id,
        _run_inspiration_bg,
        task_input=task_input,
        task_type="inspiration",
    )

    return InspirationBackgroundResponse(
        task_id=task.id,
        message="后台任务已创建",
    )


class InspirationRetryRequest(BaseModel):
    task_id: str


class InspirationRetryResponse(BaseModel):
    task_id: str
    message: str


async def _generate_single_option(
    step: str,
    context: Dict[str, Any],
    user_id: str,
    db: AsyncSession,
    ai_service: AIService
) -> str:
    """内部辅助函数：生成单个选项（不重试）"""
    template_key_map = {
        "title": ("INSPIRATION_TITLE_SYSTEM", "INSPIRATION_TITLE_USER"),
        "description": ("INSPIRATION_DESCRIPTION_SYSTEM", "INSPIRATION_DESCRIPTION_USER"),
        "theme": ("INSPIRATION_THEME_SYSTEM", "INSPIRATION_THEME_USER"),
        "genre": ("INSPIRATION_GENRE_SYSTEM", "INSPIRATION_GENRE_USER")
    }
    template_keys = template_key_map.get(step)
    if not template_keys:
        raise ValueError(f"不支持的步骤: {step}")

    system_key, user_key = template_keys
    system_template = await PromptService.get_template(system_key, user_id, db)
    user_template = await PromptService.get_template(user_key, user_id, db)

    format_params = {
        "initial_idea": context.get("initial_idea", context.get("description", "")),
        "title": context.get("title", ""),
        "description": context.get("description", ""),
        "theme": context.get("theme", "")
    }
    system_prompt = system_template.format(**format_params)
    user_prompt = user_template.format(**format_params)

    temperature = TEMPERATURE_SETTINGS.get(step, 0.7)
    accumulated_text = ""
    async for chunk in ai_service.generate_text_stream(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        auto_mcp=False,  # 禁用MCP，避免工具干扰简单选项生成
        max_tokens=4000,  # 确保有足够空间生成完整JSON
    ):
        accumulated_text += chunk

    cleaned_content = ai_service._clean_json_response(accumulated_text)
    result = loads_json(cleaned_content)

    if "options" in result and result["options"]:
        return result["options"][0]
    raise ValueError(f"生成{step}失败")


async def _generate_genre_options(
    context: Dict[str, Any],
    user_id: str,
    db: AsyncSession,
    ai_service: AIService
) -> list:
    """内部辅助函数：生成类型选项列表（用于多选）"""
    template_key_map = {
        "genre": ("INSPIRATION_GENRE_SYSTEM", "INSPIRATION_GENRE_USER")
    }
    template_keys = template_key_map.get("genre")
    if not template_keys:
        raise ValueError("不支持的步骤: genre")

    system_key, user_key = template_keys
    system_template = await PromptService.get_template(system_key, user_id, db)
    user_template = await PromptService.get_template(user_key, user_id, db)

    format_params = {
        "initial_idea": context.get("initial_idea", context.get("description", "")),
        "title": context.get("title", ""),
        "description": context.get("description", ""),
        "theme": context.get("theme", "")
    }
    system_prompt = system_template.format(**format_params)
    user_prompt = user_template.format(**format_params)

    temperature = TEMPERATURE_SETTINGS.get("genre", 0.7)
    accumulated_text = ""
    async for chunk in ai_service.generate_text_stream(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        auto_mcp=False,  # 禁用MCP，避免工具干扰简单选项生成
        max_tokens=4000,  # 确保有足够空间生成完整JSON
    ):
        accumulated_text += chunk

    cleaned_content = ai_service._clean_json_response(accumulated_text)
    result = loads_json(cleaned_content)

    if "options" in result and result["options"]:
        return result["options"]
    raise ValueError("生成genre失败")


class InspirationAutoRequest(BaseModel):
    initial_idea: str


class InspirationAutoResponse(BaseModel):
    task_id: str
    message: str


@router.post("/retry", response_model=InspirationRetryResponse)
async def retry_inspiration_task(
    data: InspirationRetryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """重试失败的灵感创建任务"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要登录")

    # 获取原任务
    old_task = await BackgroundTaskService.get_task(data.task_id, user_id, db)
    if not old_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if old_task.task_type != "inspiration":
        raise HTTPException(status_code=400, detail="只能重试灵感创建任务")

    if old_task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在运行中，无法重试")

    # 保存原任务的 task_input
    task_input = old_task.task_input or {}
    task_input["user_id"] = user_id

    # 删除旧任务
    await db.delete(old_task)
    await db.commit()

    # 创建新任务，使用原任务的 task_input
    task = await BackgroundTaskService.create_task(
        user_id=user_id,
        project_id=None,
        task_type="inspiration",
        task_input=task_input,
        db=db,
    )

    await background_task_service.spawn_background_task(
        task.id,
        user_id,
        _run_inspiration_bg,
        task_input=task_input,
        task_type="inspiration",
    )

    return InspirationRetryResponse(
        task_id=task.id,
        message="任务已重新创建",
    )


@router.post("/auto", response_model=InspirationAutoResponse)
async def create_inspiration_auto_task(
    data: InspirationAutoRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """一键灵感后台模式：AI自动生成所有答案并创建后台任务"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要登录")

    # 创建后台任务，只传递 initial_idea
    task_input = {
        "initial_idea": data.initial_idea,
    }

    task = await BackgroundTaskService.create_task(
        user_id=user_id,
        project_id=None,
        task_type="inspiration",
        task_input=task_input,
        db=db,
    )

    task_input["user_id"] = user_id
    await background_task_service.spawn_background_task(
        task.id,
        user_id,
        _run_inspiration_auto_bg,
        task_input=task_input,
        task_type="inspiration",
    )

    return InspirationAutoResponse(
        task_id=task.id,
        message="后台任务已创建",
    )
