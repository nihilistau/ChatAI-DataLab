from __future__ import annotations

"""Background dispatcher that executes graph runs asynchronously."""

# @tag: backend,services,elements

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_sessionmaker
from ..repositories.elements import ElementGraphRepository, get_graph_repository
from ..schemas import GraphRead, GraphRunRead
from .elements import get_graph_executor


logger = logging.getLogger(__name__)


class GraphRunDispatcher:
	"""Schedule graph executions on background asyncio tasks."""

	def __init__(self, settings: Settings):
		self._settings = settings
		self._session_factory = get_sessionmaker()
		self._tasks: dict[str, asyncio.Task[None]] = {}

	async def enqueue(
		self,
		run: GraphRunRead,
		graph: GraphRead,
		overrides: dict[str, dict[str, Any]],
	) -> None:
		loop = asyncio.get_running_loop()
		task = loop.create_task(self._execute_run(run, graph, overrides))
		self._tasks[run.id] = task
		task.add_done_callback(lambda _: self._tasks.pop(run.id, None))

	async def _execute_run(
		self,
		run: GraphRunRead,
		graph: GraphRead,
		overrides: dict[str, dict[str, Any]],
	) -> None:
		repository, session = self._build_repository()
		try:
			repository.update_run(run.id, status="running")
			executor = get_graph_executor()
			result = await asyncio.to_thread(executor.execute, graph, overrides)
			repository.update_run(run.id, status="succeeded", result=result)
		except Exception as exc:  # pragma: no cover - surfaced via API polling
			logger.exception("Graph run %s failed", run.id)
			repository.update_run(run.id, status="failed", error=str(exc))
		finally:
			if session is not None:
				session.close()

	def _build_repository(self) -> tuple[ElementGraphRepository, Session | None]:
		session: Session | None = None
		if not self._settings.cosmos_enabled:
			session = self._session_factory()
		repository = get_graph_repository(session=session, settings=self._settings)
		return repository, session


_GRAPH_RUN_DISPATCHER: GraphRunDispatcher | None = None


def get_graph_run_dispatcher() -> GraphRunDispatcher:
	global _GRAPH_RUN_DISPATCHER
	if _GRAPH_RUN_DISPATCHER is None:
		_GRAPH_RUN_DISPATCHER = GraphRunDispatcher(settings=get_settings())
	return _GRAPH_RUN_DISPATCHER


def set_graph_run_dispatcher(dispatcher: GraphRunDispatcher | None) -> None:
	global _GRAPH_RUN_DISPATCHER
	_GRAPH_RUN_DISPATCHER = dispatcher
