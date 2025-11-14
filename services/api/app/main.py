from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from lib.utils.db.pool import db
from services.api.app.apps.users.routes import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(1111)
    await db.connect()
    print(2222)
    yield
    # Shutdown
    print(3333)
    await db.disconnect()
    print(4444)

app = FastAPI(
    title="Project API",
    lifespan=lifespan
)


# Глобальный обработчик всех исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": exc.__class__.__name__,
                "details": exc.__repr__()
            }
        }
    )


# Подключаем роутеры
app.include_router(users_router, prefix="/users", tags=["users"])
