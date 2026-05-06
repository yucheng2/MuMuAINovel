"""Wizard流式API的非流式版本服务 - 供inspiration模块调用"""
from typing import Dict, Any
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.character import Character
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.models.career import Career, CharacterCareer
from app.models.relationship import CharacterRelationship, Organization, OrganizationMember, RelationshipType
from app.models.writing_style import WritingStyle
from app.models.project_default_style import ProjectDefaultStyle
from app.services.ai_service import AIService
from app.services.json_helper import loads_json
from app.schemas.career import AICareerSystemOutput
from app.services.prompt_service import PromptService
from app.logger import get_logger

logger = get_logger(__name__)


class WizardStreamService:
    """Wizard流式API的非流式版本服务类"""

    def __init__(self, db: AsyncSession, user_ai_service: AIService):
        self.db = db
        self.user_ai_service = user_ai_service

    async def get_owned_project(self, project_id: str, user_id: str | None) -> Project | None:
        """获取用户拥有的项目"""
        if not project_id or not user_id:
            return None
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def generate_world_building(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建项目并生成世界构建数据

        Args:
            data: 包含 title, description, theme, genre 等字段的字典

        Returns:
            包含 project_id 和世界构建数据的字典
        """
        # 提取参数
        title = data.get("title")
        description = data.get("description")
        theme = data.get("theme")
        genre = data.get("genre")
        narrative_perspective = data.get("narrative_perspective")
        target_words = data.get("target_words")
        chapter_count = data.get("chapter_count")
        character_count = data.get("character_count")
        outline_mode = data.get("outline_mode", "one-to-many")
        provider = data.get("provider")
        model = data.get("model")
        enable_mcp = data.get("enable_mcp", True)
        user_id = data.get("user_id")

        if not title or not description or not theme or not genre:
            raise ValueError("title、description、theme 和 genre 是必需的参数")

        # 获取基础提示词
        template = await PromptService.get_template("WORLD_BUILDING", user_id, self.db)
        base_prompt = PromptService.format_prompt(
            template,
            title=title,
            theme=theme,
            genre=genre or "通用类型",
            description=description or "暂无简介"
        )

        # 设置用户信息以启用MCP
        if user_id:
            self.user_ai_service.user_id = user_id
            self.user_ai_service.db_session = self.db

        # 流式生成世界观（带重试机制）
        MAX_WORLD_RETRIES = 3
        world_retry_count = 0
        world_generation_success = False
        world_data = {}
        accumulated_text = ""

        while world_retry_count < MAX_WORLD_RETRIES and not world_generation_success:
            try:
                accumulated_text = ""

                async for chunk in self.user_ai_service.generate_text_stream(
                    prompt=base_prompt,
                    provider=provider,
                    model=model,
                    tool_choice="required",
                ):
                    accumulated_text += chunk

                # 检查是否返回空响应
                if not accumulated_text or not accumulated_text.strip():
                    logger.warning(f"AI返回空世界观（尝试{world_retry_count+1}/{MAX_WORLD_RETRIES}）")
                    world_retry_count += 1
                    if world_retry_count < MAX_WORLD_RETRIES:
                        continue
                    else:
                        raise ValueError("世界观生成失败（AI多次返回为空）")

                # 解析结果
                try:
                    cleaned_text = self.user_ai_service._clean_json_response(accumulated_text)
                    world_data = loads_json(cleaned_text)
                    world_generation_success = True
                except json.JSONDecodeError as e:
                    logger.error(f"世界构建JSON解析失败（尝试{world_retry_count+1}/{MAX_WORLD_RETRIES}）: {e}")
                    world_retry_count += 1
                    if world_retry_count < MAX_WORLD_RETRIES:
                        continue
                    else:
                        raise ValueError("世界观生成失败（JSON解析错误）")

            except Exception as e:
                logger.error(f"世界构建生成异常（尝试{world_retry_count+1}/{MAX_WORLD_RETRIES}）: {type(e).__name__}: {e}")
                world_retry_count += 1
                if world_retry_count < MAX_WORLD_RETRIES:
                    continue
                else:
                    raise

        # 确保user_id存在
        if not user_id:
            raise ValueError("用户ID缺失，无法创建项目")

        # 创建项目
        project = Project(
            user_id=user_id,
            title=title,
            description=description,
            theme=theme,
            genre=genre,
            world_time_period=world_data.get("time_period"),
            world_location=world_data.get("location"),
            world_atmosphere=world_data.get("atmosphere"),
            world_rules=world_data.get("rules"),
            narrative_perspective=narrative_perspective,
            target_words=target_words,
            chapter_count=chapter_count,
            character_count=character_count,
            outline_mode=outline_mode,
            wizard_status="incomplete",
            wizard_step=1,
            status="planning"
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)

        # 自动设置默认写作风格
        try:
            result = await self.db.execute(
                select(WritingStyle).where(
                    WritingStyle.user_id.is_(None),
                    WritingStyle.order_index == 1
                ).limit(1)
            )
            first_style = result.scalar_one_or_none()

            if first_style:
                default_style = ProjectDefaultStyle(
                    project_id=project.id,
                    style_id=first_style.id
                )
                self.db.add(default_style)
                await self.db.commit()
                logger.info(f"为项目 {project.id} 自动设置默认风格: {first_style.name}")
        except Exception as e:
            logger.warning(f"设置默认写作风格失败: {e}，不影响项目创建")

        # 更新向导步骤状态
        project.wizard_step = 1
        await self.db.commit()

        logger.info(f"世界观生成完成，项目ID: {project.id}")

        return {
            "project_id": project.id,
            "time_period": world_data.get("time_period"),
            "location": world_data.get("location"),
            "atmosphere": world_data.get("atmosphere"),
            "rules": world_data.get("rules")
        }

    async def generate_career_system(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为项目生成职业体系

        Args:
            data: 包含 project_id 的字典

        Returns:
            包含职业体系数据的字典
        """
        project_id = data.get("project_id")
        provider = data.get("provider")
        model = data.get("model")
        user_id = data.get("user_id")

        if not project_id:
            raise ValueError("project_id 是必需的参数")

        # 获取项目信息
        project = await self.get_owned_project(project_id, user_id)
        if not project:
            raise ValueError("项目不存在或无权访问")

        # 设置用户信息以启用MCP
        if user_id:
            self.user_ai_service.user_id = user_id
            self.user_ai_service.db_session = self.db

        # 获取世界观数据
        world_data = {
            "time_period": project.world_time_period or "未设定",
            "location": project.world_location or "未设定",
            "atmosphere": project.world_atmosphere or "未设定",
            "rules": project.world_rules or "未设定"
        }

        # 获取职业生成提示词模板
        template = await PromptService.get_template("CAREER_SYSTEM_GENERATION", user_id, self.db)
        career_prompt = PromptService.format_prompt(
            template,
            title=project.title,
            genre=project.genre or '未设定',
            theme=project.theme or '未设定',
            description=project.description or '暂无简介',
            time_period=world_data.get('time_period', '未设定'),
            location=world_data.get('location', '未设定'),
            atmosphere=world_data.get('atmosphere', '未设定'),
            rules=world_data.get('rules', '未设定')
        )

        MAX_CAREER_RETRIES = 3
        career_retry_count = 0
        career_generation_success = False
        career_data = None

        while career_retry_count < MAX_CAREER_RETRIES and not career_generation_success:
            try:
                # 使用 LangChain structured output 生成职业体系
                try:
                    career_result = await self.user_ai_service.call_with_structured_output(
                        prompt=career_prompt,
                        output_schema=AICareerSystemOutput,
                        provider=provider,
                        model=model,
                        max_retries=MAX_CAREER_RETRIES - career_retry_count,
                    )
                    if hasattr(career_result, "model_dump"):
                        career_data = career_result.model_dump()
                    elif hasattr(career_result, "model_dump_json"):
                        career_data = json.loads(career_result.model_dump_json())
                    else:
                        career_data = career_result
                    career_generation_success = True
                except Exception as e:
                    logger.error(f"LangChain structured output 失败: {e}，尝试使用传统方法")

                    # 回退到传统流式方法
                    career_response = ""

                    async for chunk in self.user_ai_service.generate_text_stream(
                        prompt=career_prompt,
                        provider=provider,
                        model=model,
                    ):
                        career_response += chunk

                    if not career_response or not career_response.strip():
                        logger.warning(f"AI返回空职业体系（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）")
                        career_retry_count += 1
                        if career_retry_count < MAX_CAREER_RETRIES:
                            continue
                        else:
                            raise ValueError("职业体系生成失败（AI多次返回为空）")

                    # 清洗并解析JSON
                    cleaned_response = self.user_ai_service._clean_json_response(career_response)
                    career_data = loads_json(cleaned_response)
                    career_generation_success = True

            except json.JSONDecodeError as e:
                logger.error(f"职业体系JSON解析失败（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）: {e}")
                career_retry_count += 1
                if career_retry_count < MAX_CAREER_RETRIES:
                    continue
                else:
                    raise ValueError("职业体系解析失败（已达最大重试次数）")
            except Exception as e:
                logger.error(f"职业体系生成异常（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）: {e}")
                career_retry_count += 1
                if career_retry_count < MAX_CAREER_RETRIES:
                    continue
                else:
                    raise

        # 保存主职业
        main_careers_created = []
        for idx, career_info in enumerate(career_data.get("main_careers", [])):
            try:
                stages_json = json.dumps(career_info.get("stages", []), ensure_ascii=False)
                attribute_bonuses = career_info.get("attribute_bonuses")
                attribute_bonuses_json = json.dumps(attribute_bonuses, ensure_ascii=False) if attribute_bonuses else None

                career = Career(
                    project_id=project.id,
                    name=career_info.get("name", f"未命名主职业{idx+1}"),
                    type="main",
                    description=career_info.get("description"),
                    category=career_info.get("category"),
                    stages=stages_json,
                    max_stage=career_info.get("max_stage", 10),
                    requirements=career_info.get("requirements"),
                    special_abilities=career_info.get("special_abilities"),
                    worldview_rules=career_info.get("worldview_rules"),
                    attribute_bonuses=attribute_bonuses_json,
                    source="ai"
                )
                self.db.add(career)
                await self.db.flush()
                main_careers_created.append(career.name)
                logger.info(f"创建主职业：{career.name}")
            except Exception as e:
                logger.error(f"创建主职业失败：{str(e)}")
                continue

        # 保存副职业
        sub_careers_created = []
        for idx, career_info in enumerate(career_data.get("sub_careers", [])):
            try:
                stages_json = json.dumps(career_info.get("stages", []), ensure_ascii=False)
                attribute_bonuses = career_info.get("attribute_bonuses")
                attribute_bonuses_json = json.dumps(attribute_bonuses, ensure_ascii=False) if attribute_bonuses else None

                career = Career(
                    project_id=project.id,
                    name=career_info.get("name", f"未命名副职业{idx+1}"),
                    type="sub",
                    description=career_info.get("description"),
                    category=career_info.get("category"),
                    stages=stages_json,
                    max_stage=career_info.get("max_stage", 5),
                    requirements=career_info.get("requirements"),
                    special_abilities=career_info.get("special_abilities"),
                    worldview_rules=career_info.get("worldview_rules"),
                    attribute_bonuses=attribute_bonuses_json,
                    source="ai"
                )
                self.db.add(career)
                await self.db.flush()
                sub_careers_created.append(career.name)
                logger.info(f"创建副职业：{career.name}")
            except Exception as e:
                logger.error(f"创建副职业失败：{str(e)}")
                continue

        # 更新向导步骤状态
        project.wizard_step = 2
        await self.db.commit()

        logger.info(f"职业体系生成完成：主职业{len(main_careers_created)}个，副职业{len(sub_careers_created)}个")

        return {
            "project_id": project.id,
            "main_careers_count": len(main_careers_created),
            "sub_careers_count": len(sub_careers_created),
            "main_careers": main_careers_created,
            "sub_careers": sub_careers_created
        }

    async def generate_characters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为项目生成角色

        Args:
            data: 包含 project_id, count 等字段的字典

        Returns:
            包含角色列表的字典
        """
        project_id = data.get("project_id")
        count = data.get("count", 5)
        world_context = data.get("world_context")
        theme = data.get("theme", "")
        genre = data.get("genre", "")
        requirements = data.get("requirements", "")
        provider = data.get("provider")
        model = data.get("model")
        user_id = data.get("user_id")

        if not project_id:
            raise ValueError("project_id 是必需的参数")

        # 验证项目
        project = await self.get_owned_project(project_id, user_id)
        if not project:
            raise ValueError("项目不存在或无权访问")

        project.wizard_step = 2

        world_context = world_context or {
            "time_period": project.world_time_period or "未设定",
            "location": project.world_location or "未设定",
            "atmosphere": project.world_atmosphere or "未设定",
            "rules": project.world_rules or "未设定"
        }

        # 设置用户信息以启用MCP
        if user_id:
            self.user_ai_service.user_id = user_id
            self.user_ai_service.db_session = self.db

        # 获取项目的职业列表
        career_result = await self.db.execute(
            select(Career).where(Career.project_id == project_id).order_by(Career.type, Career.id)
        )
        careers = career_result.scalars().all()

        main_careers = [c for c in careers if c.type == "main"]
        sub_careers = [c for c in careers if c.type == "sub"]

        # 构建职业上下文
        careers_context = ""
        if main_careers or sub_careers:
            careers_context = "\n\n【职业体系】\n"
            if main_careers:
                careers_context += "主职业：\n"
                for career in main_careers:
                    careers_context += f"- {career.name}: {career.description or '暂无描述'}\n"
            if sub_careers:
                careers_context += "\n副职业：\n"
                for career in sub_careers:
                    careers_context += f"- {career.name}: {career.description or '暂无描述'}\n"

            careers_context += "\n请为每个角色分配职业：\n"
            careers_context += "- 每个角色必须有1个主职业（从上述主职业中选择）\n"
            careers_context += "- 每个角色可以有0-2个副职业（从上述副职业中选择，可选）\n"
            careers_context += "- 主职业初始阶段建议为1-3\n"
            careers_context += "- 副职业初始阶段建议为1-2\n"
            careers_context += "- 请在返回的JSON中包含 career_assignment 字段\n"

        # 分批生成角色
        BATCH_SIZE = 5
        MAX_RETRIES = 3
        all_characters = []
        total_batches = (count + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(total_batches):
            remaining = count - len(all_characters)
            current_batch_size = min(BATCH_SIZE, remaining)

            if current_batch_size <= 0:
                break

            retry_count = 0
            batch_success = False
            batch_error_message = ""

            while retry_count < MAX_RETRIES and not batch_success:
                try:
                    # 构建已生成角色上下文
                    existing_chars_context = ""
                    if all_characters:
                        existing_chars_context = "\n\n【已生成的角色】:\n"
                        for char in all_characters:
                            existing_chars_context += f"- {char.get('name')}: {char.get('role_type', '未知')}, {char.get('personality', '暂无')[:50]}...\n"
                        existing_chars_context += "\n请确保新角色与已有角色形成合理的关系网络和互动。\n"

                    # 构建批次要求
                    if batch_idx == 0:
                        if current_batch_size == 1:
                            batch_requirements = f"{requirements}\n请生成1个主角(protagonist)"
                        else:
                            batch_requirements = f"{requirements}\n请精确生成{current_batch_size}个角色:1个主角(protagonist)和{current_batch_size-1}个核心配角(supporting)"
                    else:
                        batch_requirements = f"{requirements}\n请精确生成{current_batch_size}个角色{existing_chars_context}"
                        if batch_idx == total_batches - 1:
                            batch_requirements += "\n可以包含组织或反派(antagonist)"
                        else:
                            batch_requirements += "\n主要是配角(supporting)和反派(antagonist)"

                    # 获取自定义提示词模板
                    template = await PromptService.get_template("CHARACTERS_BATCH_GENERATION", user_id, self.db)
                    base_prompt = PromptService.format_prompt(
                        template,
                        count=current_batch_size,
                        time_period=world_context.get("time_period", ""),
                        location=world_context.get("location", ""),
                        atmosphere=world_context.get("atmosphere", ""),
                        rules=world_context.get("rules", ""),
                        theme=theme or project.theme or "",
                        genre=genre or project.genre or "",
                        requirements=batch_requirements + careers_context
                    )

                    # 流式生成
                    accumulated_text = ""

                    async for chunk in self.user_ai_service.generate_text_stream(
                        prompt=base_prompt,
                        provider=provider,
                        model=model,
                        tool_choice="required",
                    ):
                        accumulated_text += chunk

                    # 解析批次结果
                    cleaned_text = self.user_ai_service._clean_json_response(accumulated_text)
                    characters_data = loads_json(cleaned_text)
                    if not isinstance(characters_data, list):
                        characters_data = [characters_data]

                    # 严格验证生成数量
                    if len(characters_data) != current_batch_size:
                        error_msg = f"批次{batch_idx+1}生成数量不正确: 期望{current_batch_size}个, 实际{len(characters_data)}个"
                        logger.error(error_msg)
                        retry_count += 1
                        if retry_count < MAX_RETRIES:
                            continue
                        else:
                            raise ValueError(error_msg)

                    all_characters.extend(characters_data)
                    batch_success = True
                    logger.info(f"批次{batch_idx+1}成功添加{len(characters_data)}个角色,当前总数{len(all_characters)}/{count}")

                except json.JSONDecodeError as e:
                    logger.error(f"批次{batch_idx+1}解析失败(尝试{retry_count+1}/{MAX_RETRIES}): {e}")
                    batch_error_message = f"JSON解析失败: {str(e)}"
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        continue
                    else:
                        raise
                except Exception as e:
                    logger.error(f"批次{batch_idx+1}生成异常(尝试{retry_count+1}/{MAX_RETRIES}): {e}")
                    batch_error_message = f"生成异常: {str(e)}"
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        continue
                    else:
                        raise

            if not batch_success:
                error_msg = f"批次{batch_idx+1}在{MAX_RETRIES}次重试后仍然失败"
                if batch_error_message:
                    error_msg += f": {batch_error_message}"
                raise ValueError(error_msg)

        # 预处理：构建名称集合
        valid_entity_names = set()
        valid_organization_names = set()

        for char_data in all_characters:
            entity_name = char_data.get("name", "")
            if entity_name:
                valid_entity_names.add(entity_name)
                if char_data.get("is_organization", False):
                    valid_organization_names.add(entity_name)

        # 清理幻觉引用
        for char_data in all_characters:
            if "relationships_array" in char_data and isinstance(char_data["relationships_array"], list):
                original_rels = char_data["relationships_array"]
                valid_rels = []
                for rel in original_rels:
                    target_name = rel.get("target_character_name", "")
                    if target_name in valid_entity_names:
                        valid_rels.append(rel)
                char_data["relationships_array"] = valid_rels

            if "organization_memberships" in char_data and isinstance(char_data["organization_memberships"], list):
                original_orgs = char_data["organization_memberships"]
                valid_orgs = []
                for org_mem in original_orgs:
                    org_name = org_mem.get("organization_name", "")
                    if org_name in valid_organization_names:
                        valid_orgs.append(org_mem)
                char_data["organization_memberships"] = valid_orgs

        # 创建所有Character记录
        created_characters = []
        character_name_to_obj = {}

        for char_data in all_characters:
            relationships_text = ""
            relationships_array = char_data.get("relationships_array", [])
            if relationships_array and isinstance(relationships_array, list):
                rel_descriptions = []
                for rel in relationships_array:
                    target = rel.get("target_character_name", "未知")
                    rel_type = rel.get("relationship_type", "关系")
                    desc = rel.get("description", "")
                    rel_descriptions.append(f"{target}({rel_type}): {desc}")
                relationships_text = "; ".join(rel_descriptions)
            elif isinstance(char_data.get("relationships"), dict):
                relationships_text = json.dumps(char_data.get("relationships"), ensure_ascii=False)
            elif isinstance(char_data.get("relationships"), str):
                relationships_text = char_data.get("relationships")

            is_organization = char_data.get("is_organization", False)

            character = Character(
                project_id=project_id,
                name=char_data.get("name", "未命名角色"),
                age=str(char_data.get("age", "")) if not is_organization else None,
                gender=char_data.get("gender") if not is_organization else None,
                is_organization=is_organization,
                role_type=char_data.get("role_type", "supporting"),
                personality=char_data.get("personality", ""),
                background=char_data.get("background", ""),
                appearance=char_data.get("appearance", ""),
                relationships=relationships_text,
                organization_type=char_data.get("organization_type") if is_organization else None,
                organization_purpose=char_data.get("organization_purpose") if is_organization else None,
                traits=json.dumps(char_data.get("traits", []), ensure_ascii=False) if char_data.get("traits") else None
            )
            self.db.add(character)
            created_characters.append((character, char_data))

        await self.db.flush()

        # 为角色分配职业
        if main_careers or sub_careers:
            career_name_to_obj = {c.name: c for c in careers}

            for character, char_data in created_characters:
                if character.is_organization:
                    continue

                try:
                    career_assignment = char_data.get("career_assignment", {})

                    main_career_name = career_assignment.get("main_career")
                    main_career_stage = career_assignment.get("main_stage", 1)

                    if main_career_name and main_career_name in career_name_to_obj:
                        main_career = career_name_to_obj[main_career_name]

                        char_career = CharacterCareer(
                            character_id=character.id,
                            career_id=main_career.id,
                            career_type="main",
                            current_stage=min(main_career_stage, main_career.max_stage),
                            stage_progress=0
                        )
                        self.db.add(char_career)

                        character.main_career_id = main_career.id
                        character.main_career_stage = char_career.current_stage

                    sub_career_assignments = career_assignment.get("sub_careers", [])
                    sub_career_list = []

                    for sub_assign in sub_career_assignments[:2]:
                        sub_career_name = sub_assign.get("career")
                        sub_career_stage = sub_assign.get("stage", 1)

                        if sub_career_name and sub_career_name in career_name_to_obj:
                            sub_career = career_name_to_obj[sub_career_name]

                            char_career = CharacterCareer(
                                character_id=character.id,
                                career_id=sub_career.id,
                                career_type="sub",
                                current_stage=min(sub_career_stage, sub_career.max_stage),
                                stage_progress=0
                            )
                            self.db.add(char_career)

                            sub_career_list.append({
                                "career_id": sub_career.id,
                                "stage": char_career.current_stage
                            })

                    if sub_career_list:
                        character.sub_careers = json.dumps(sub_career_list, ensure_ascii=False)

                except Exception as e:
                    logger.warning(f"分配职业失败：{character.name} - {str(e)}")
                    continue

            await self.db.flush()

        # 刷新并建立名称映射
        for character, _ in created_characters:
            await self.db.refresh(character)
            character_name_to_obj[character.name] = character

        # 创建组织记录
        organization_name_to_obj = {}

        for character, char_data in created_characters:
            if character.is_organization:
                org_check = await self.db.execute(
                    select(Organization).where(Organization.character_id == character.id)
                )
                existing_org = org_check.scalar_one_or_none()

                if not existing_org:
                    org = Organization(
                        character_id=character.id,
                        project_id=project_id,
                        member_count=0,
                        power_level=char_data.get("power_level", 50),
                        location=char_data.get("location"),
                        motto=char_data.get("motto"),
                        color=char_data.get("color")
                    )
                    self.db.add(org)
                else:
                    org = existing_org

                organization_name_to_obj[character.name] = org

        await self.db.flush()

        # 刷新角色以获取ID
        for character, _ in created_characters:
            await self.db.refresh(character)

        # 创建角色间关系
        for character, char_data in created_characters:
            if character.is_organization:
                continue

            relationships_data = char_data.get("relationships_array", [])
            if not relationships_data and isinstance(char_data.get("relationships"), list):
                relationships_data = char_data.get("relationships")

            if relationships_data and isinstance(relationships_data, list):
                for rel in relationships_data:
                    try:
                        target_name = rel.get("target_character_name")
                        if not target_name:
                            continue

                        target_char = character_name_to_obj.get(target_name)

                        if target_char:
                            existing_rel = await self.db.execute(
                                select(CharacterRelationship).where(
                                    CharacterRelationship.project_id == project_id,
                                    CharacterRelationship.character_from_id == character.id,
                                    CharacterRelationship.character_to_id == target_char.id
                                )
                            )
                            if existing_rel.scalar_one_or_none():
                                continue

                            relationship = CharacterRelationship(
                                project_id=project_id,
                                character_from_id=character.id,
                                character_to_id=target_char.id,
                                relationship_name=rel.get("relationship_type", "未知关系"),
                                intimacy_level=rel.get("intimacy_level", 50),
                                description=rel.get("description", ""),
                                started_at=rel.get("started_at"),
                                source="ai"
                            )

                            rel_type_result = await self.db.execute(
                                select(RelationshipType).where(
                                    RelationshipType.name == rel.get("relationship_type")
                                )
                            )
                            rel_type = rel_type_result.scalar_one_or_none()
                            if rel_type:
                                relationship.relationship_type_id = rel_type.id

                            self.db.add(relationship)
                        else:
                            logger.warning(f"目标角色不存在：{character.name} -> {target_name}（可能是AI幻觉）")
                    except Exception as e:
                        logger.warning(f"创建关系失败：{character.name} - {str(e)}")
                        continue

        # 创建组织成员关系
        for character, char_data in created_characters:
            if character.is_organization:
                continue

            org_memberships = char_data.get("organization_memberships", [])
            if org_memberships and isinstance(org_memberships, list):
                for membership in org_memberships:
                    try:
                        org_name = membership.get("organization_name")
                        if not org_name:
                            continue

                        org = organization_name_to_obj.get(org_name)

                        if org:
                            existing_member = await self.db.execute(
                                select(OrganizationMember).where(
                                    OrganizationMember.organization_id == org.id,
                                    OrganizationMember.character_id == character.id
                                )
                            )
                            if existing_member.scalar_one_or_none():
                                continue

                            member = OrganizationMember(
                                organization_id=org.id,
                                character_id=character.id,
                                position=membership.get("position", "成员"),
                                rank=membership.get("rank", 0),
                                loyalty=membership.get("loyalty", 50),
                                joined_at=membership.get("joined_at"),
                                status=membership.get("status", "active"),
                                source="ai"
                            )
                            self.db.add(member)

                            org.member_count += 1
                        else:
                            logger.debug(f"组织引用已被清理：{character.name} -> {org_name}")
                    except Exception as e:
                        logger.warning(f"添加组织成员失败：{character.name} - {str(e)}")
                        continue

        # 更新项目
        project.character_count = len(created_characters)
        project.wizard_step = 3
        logger.info(f"更新项目角色数量: {project.character_count}")

        await self.db.commit()

        created_characters_objs = [char for char, _ in created_characters]

        return {
            "message": f"成功生成{len(created_characters_objs)}个角色/组织（分{total_batches}批完成）",
            "count": len(created_characters_objs),
            "batches": total_batches,
            "characters": [
                {
                    "id": char.id,
                    "project_id": char.project_id,
                    "name": char.name,
                    "age": char.age,
                    "gender": char.gender,
                    "is_organization": char.is_organization,
                    "role_type": char.role_type,
                    "personality": char.personality,
                    "background": char.background,
                    "appearance": char.appearance,
                    "relationships": "",
                    "organization_type": char.organization_type,
                    "organization_purpose": char.organization_purpose,
                    "organization_members": "",
                    "traits": char.traits,
                    "created_at": char.created_at.isoformat() if char.created_at else None,
                    "updated_at": char.updated_at.isoformat() if char.updated_at else None
                } for char in created_characters_objs
            ]
        }

    async def generate_outline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为项目生成大纲

        Args:
            data: 包含 project_id 等字段的字典

        Returns:
            包含大纲和章节信息的字典
        """
        project_id = data.get("project_id")
        outline_count = data.get("chapter_count", 3)
        narrative_perspective = data.get("narrative_perspective")
        target_words = data.get("target_words", 100000)
        requirements = data.get("requirements", "")
        provider = data.get("provider")
        model = data.get("model")
        enable_mcp = data.get("enable_mcp", True)
        user_id = data.get("user_id")

        # 获取项目信息
        project = await self.get_owned_project(project_id, user_id)
        if not project:
            raise ValueError("项目不存在或无权访问")

        # 设置用户信息以启用MCP
        if user_id:
            self.user_ai_service.user_id = user_id
            self.user_ai_service.db_session = self.db

        # 获取角色信息
        result = await self.db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        characters = result.scalars().all()

        characters_info = "\n".join([
            f"- {char.name} ({'组织' if char.is_organization else '角色'}, {char.role_type}): {char.personality[:100] if char.personality else '暂无描述'}"
            for char in characters
        ])

        # 准备提示词
        outline_requirements = f"{requirements}\n\n【重要说明】这是小说的开局部分，请生成{outline_count}个大纲节点，重点关注：\n"
        outline_requirements += "1. 引入主要角色和世界观设定\n"
        outline_requirements += "2. 建立主线冲突和故事钩子\n"
        outline_requirements += "3. 展开初期情节，为后续发展埋下伏笔\n"
        outline_requirements += "4. 不要试图完结故事，这只是开始部分\n"
        outline_requirements += "5. 不要在JSON字符串值中使用中文引号（""''），请使用【】或《》标记\n"

        # 获取自定义提示词模板
        template = await PromptService.get_template("OUTLINE_CREATE", user_id, self.db)
        outline_prompt = PromptService.format_prompt(
            template,
            title=project.title,
            theme=project.theme or "未设定",
            genre=project.genre or "通用",
            chapter_count=outline_count,
            narrative_perspective=narrative_perspective,
            target_words=target_words // 10,
            time_period=project.world_time_period or "未设定",
            location=project.world_location or "未设定",
            atmosphere=project.world_atmosphere or "未设定",
            rules=project.world_rules or "未设定",
            characters_info=characters_info or "暂无角色信息",
            mcp_references="",
            requirements=outline_requirements
        )

        # 流式生成大纲
        accumulated_text = ""

        async for chunk in self.user_ai_service.generate_text_stream(
            prompt=outline_prompt,
            provider=provider,
            model=model,
        ):
            accumulated_text += chunk

        # 解析大纲结果
        try:
            cleaned_text = self.user_ai_service._clean_json_response(accumulated_text)
            outline_data = loads_json(cleaned_text)
            if not isinstance(outline_data, list):
                outline_data = [outline_data]
        except json.JSONDecodeError as e:
            logger.error(f"大纲JSON解析失败: {e}")
            raise ValueError("大纲生成失败，请重试")

        # 保存大纲到数据库
        created_outlines = []
        for index, outline_item in enumerate(outline_data[:outline_count], 1):
            outline = Outline(
                project_id=project_id,
                title=outline_item.get("title", f"第{index}节"),
                content=outline_item.get("summary", outline_item.get("content", "")),
                structure=json.dumps(outline_item, ensure_ascii=False),
                order_index=index
            )
            self.db.add(outline)
            created_outlines.append(outline)

        await self.db.flush()
        for outline in created_outlines:
            await self.db.refresh(outline)

        logger.info(f"成功创建{len(created_outlines)}个大纲节点")

        # 角色校验
        try:
            from app.services.auto_character_service import get_auto_character_service

            auto_char_service = get_auto_character_service(self.user_ai_service)
            char_check_result = await auto_char_service.check_and_create_missing_characters(
                project_id=project_id,
                outline_data_list=outline_data[:outline_count],
                db=self.db,
                user_id=user_id,
                enable_mcp=enable_mcp
            )
            if char_check_result["created_count"] > 0:
                created_names = [c.name for c in char_check_result["created_characters"]]
                logger.info(f"向导大纲：自动创建了 {char_check_result['created_count']} 个角色: {', '.join(created_names)}")
        except Exception as e:
            logger.error(f"向导大纲角色校验失败（不影响主流程）: {e}")

        # 组织校验
        try:
            from app.services.auto_organization_service import get_auto_organization_service

            auto_org_service = get_auto_organization_service(self.user_ai_service)
            org_check_result = await auto_org_service.check_and_create_missing_organizations(
                project_id=project_id,
                outline_data_list=outline_data[:outline_count],
                db=self.db,
                user_id=user_id,
                enable_mcp=enable_mcp
            )
            if org_check_result["created_count"] > 0:
                created_names = [c.name for c in org_check_result["created_organizations"]]
                logger.info(f"向导大纲：自动创建了 {org_check_result['created_count']} 个组织: {', '.join(created_names)}")
        except Exception as e:
            logger.error(f"向导大纲组织校验失败（不影响主流程）: {e}")

        # 根据大纲模式决定是否自动创建章节
        created_chapters = []
        if project.outline_mode == 'one-to-one':
            for outline in created_outlines:
                chapter = Chapter(
                    project_id=project_id,
                    title=outline.title,
                    content="",
                    outline_id=None,
                    chapter_number=outline.order_index,
                    status="pending"
                )
                self.db.add(chapter)
                created_chapters.append(chapter)

            await self.db.flush()
            for chapter in created_chapters:
                await self.db.refresh(chapter)

            logger.info(f"一对一模式：自动创建了{len(created_chapters)}个章节")
        else:
            logger.info(f"细化模式：跳过章节创建，用户可在大纲页面手动展开")

        # 更新项目信息
        project.chapter_count = len(created_chapters)
        project.narrative_perspective = narrative_perspective
        project.target_words = target_words
        project.status = "writing"
        project.wizard_status = "completed"
        project.wizard_step = 4

        await self.db.commit()

        logger.info(f"向导大纲生成完成：创建大纲节点{len(created_outlines)}个，创建章节{len(created_chapters)}个")

        # 构建结果消息
        if project.outline_mode == 'one-to-one':
            result_message = f"成功生成{len(created_outlines)}个大纲节点并自动创建{len(created_chapters)}个章节（传统模式）"
            result_note = "已自动创建章节，可直接生成内容"
        else:
            result_message = f"成功生成{len(created_outlines)}个大纲节点（细化模式，可在大纲页面手动展开）"
            result_note = "可在大纲页面展开为多个章节"

        return {
            "message": result_message,
            "outline_count": len(created_outlines),
            "chapter_count": len(created_chapters),
            "outline_mode": project.outline_mode,
            "outlines": [
                {
                    "id": outline.id,
                    "order_index": outline.order_index,
                    "title": outline.title,
                    "content": outline.content[:100] + "..." if len(outline.content) > 100 else outline.content,
                    "note": result_note
                } for outline in created_outlines
            ],
            "chapters": [
                {
                    "id": chapter.id,
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "status": chapter.status
                } for chapter in created_chapters
            ] if created_chapters else []
        }
