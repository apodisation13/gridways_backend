from contextlib import asynccontextmanager
import json
import logging.config

from fastapi import FastAPI, HTTPException, Header, Response, status
from jose import JWTError, jwt
from lib.utils.elk.elastic_logger import ElasticLoggerManager
from lib.utils.elk.elastic_tracer import ElasticTracerManager
from lib.utils.schemas.base import generate_uuid4_str
from services.frontend_logs.app.config import get_config as get_app_settings
from services.frontend_logs.app.middlewares import set_middlewares


apm_manager = ElasticTracerManager()
config = get_app_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = config

    logging.config.dictConfig(config.LOGGING)

    elastic_logger_manager = ElasticLoggerManager()
    elastic_logger_manager.initialize(
        config=config,
        service_name="frontend-logs",
        delay_seconds=5,
    )
    apm_manager.initialize(
        config=config,
        service_name="frontend-logs",
    )

    logger.info("Starting frontend-logs service")

    yield


app = FastAPI(
    title="Gridways frontend logs",
    lifespan=lifespan,
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

set_middlewares(app, config, apm_manager)


def validate_token(token: str) -> bool:
    try:
        payload = jwt.decode(
            token,
            config.USER_PASSWORD_SECRET_KEY,
            algorithms=[config.ALGORITHM],
            options={"verify_exp": True, "require_exp": True},
        )
    except (JWTError, TypeError):
        return False

    return payload.get("type") == "access_token"


@app.post("/api/frontend_logs", status_code=status.HTTP_200_OK)
def post_frontend_logs(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> Response:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token or not validate_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    events = payload.get("events", [])
    if not isinstance(events, list) or any(not isinstance(event, dict) for event in events):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="events must be a list of objects",
        )

    for event in events:
        event_id = event.get("event_id") or generate_uuid4_str()
        message = json.dumps(event, ensure_ascii=False)
        extra = {"event_id": event_id}

        if event.get("level") == "error":
            logger.error("%s", message, extra=extra)
        elif event.get("level") == "warning":
            logger.warning("%s", message, extra=extra)
        else:
            logger.info("%s", message, extra=extra)

    return Response(status_code=status.HTTP_200_OK)
