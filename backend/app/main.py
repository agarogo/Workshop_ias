from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.configs import router as configs_router
from app.api.routers.files import router as files_router
from app.api.routers.health import router as health_router
from app.api.routers.runs import router as runs_router
from app.api.routers.suites import router as suites_router
from app.api.routers.tests import router as tests_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="BenchFile",
    description="File-based benchmark/config storage and PromptBench launcher",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(configs_router)
app.include_router(tests_router)
app.include_router(suites_router)
app.include_router(runs_router)
app.include_router(files_router)
