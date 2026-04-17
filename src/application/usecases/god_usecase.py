import logging
from typing import Any, Dict, List
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from src.prompt import SYSTEM_PROMPT
from src.application.usecases.base_usecase import BaseUseCase, BaseUseCaseConfig
from src.config import settings
from src.infrastructure.llm.factory import get_llm
from src.graph.state import AgentState

logger = logging.getLogger(__name__)


class GodUseCase(BaseUseCase):
    def __init__(self, tools_resolver=None, llm_factory=None):
        config = BaseUseCaseConfig(
            model_name="default",
            system_prompt_template="",
        )
        super().__init__(tools_resolver=tools_resolver, llm_factory=llm_factory, config=config)

    def _get_tools(self, state: AgentState) -> List[BaseTool]:
        """В оркестраторе возвращает список доступных инструментов"""
        return []

    def _build_system_prompt(self, state: AgentState, tools: List[BaseTool]) -> str:
        """Получить системный промпт"""
        return SYSTEM_PROMPT

    async def run(self, state: AgentState, *, stream: bool = False) -> Dict[str, Any]:
        messages = list(state.get("messages") or [])
        if not messages:
            return {}

        raw_runtime_params = state.get("runtime_params") or {}
        runtime_params = dict(raw_runtime_params)

        allowed_keys = {
            "temperature",
            "top_p",
            "top_k",
            "num_ctx",
            "num_predict",
            "seed",
            "think",
        }
        runtime_params = {
            key: value
            for key, value in runtime_params.items()
            if key in allowed_keys and value is not None
        }

        logger.debug(
            "GodUseCase runtime params: %s",
            runtime_params,
        )

        # Параметры загрузятся из .env
        llm = get_llm(
            "default",
            model=settings.LLM_MODEL,
            stream=stream,
            **runtime_params,
        )

        system = self._build_system_prompt(state, [])
        prompt = [SystemMessage(content=system)] + messages

        if stream:
            response = await llm.ainvoke(prompt)  # Пока что use ainvoke
        else:
            response = await llm.ainvoke(prompt)

        if not isinstance(response, AIMessage):
            response = AIMessage(content=str(response) if response else "")

        return {
            "messages": [response],
            "response": response,
        }