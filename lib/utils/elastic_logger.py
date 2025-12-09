import logging
import time
import sys
from datetime import datetime
import os
import threading

# КРИТИЧНО: Отключаем логи ДО импорта Elasticsearch!
logging.getLogger("elastic_transport").setLevel(logging.WARNING)
logging.getLogger("elastic_transport.transport").setLevel(logging.WARNING)
logging.getLogger("elasticsearch").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

# Теперь импортируем
from elasticsearch import Elasticsearch


class ElasticsearchHandler(logging.Handler):
    """Хендлер для отправки логов в Elasticsearch"""

    # Список логгеров, которые нужно игнорировать
    IGNORED_LOGGERS = {
        'elasticsearch',
        'elastic_transport',
        'elastic_transport.transport',
        'urllib3',
        'urllib3.connectionpool',
        'urllib3.util',
        'urllib3.util.retry',
        'es_handler_'
    }

    def __init__(self, service_name="myapp", retry_count=3):
        super().__init__()
        self.service_name = service_name
        self.retry_count = retry_count
        self.es = None
        self._sending = threading.local()  # Для предотвращения рекурсии
        self._init_elasticsearch()

    def _init_elasticsearch(self):
        """Инициализация подключения к Elasticsearch"""
        try:
            self.es = Elasticsearch(
                ['http://elasticsearch:9200'],
                verify_certs=False,
                ssl_show_warn=False,
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True,
                basic_auth=("elastic", "YourStrongPassword123!"),
            )

            info = self.es.info()
            version = info['version']['number']
            print(f"✅ Подключение к Elasticsearch {version} установлено")

        except Exception as e:
            print(f"❌ Ошибка подключения к Elasticsearch: {e}")
            self.es = None

    def emit(self, record):
        """Отправка лога в Elasticsearch"""

        # КРИТИЧНО: Игнорируем логи от ES библиотек
        if any(record.name.startswith(ignored) for ignored in self.IGNORED_LOGGERS):
            return

        # Предотвращаем рекурсию
        if getattr(self._sending, 'in_progress', False):
            return

        if not self.es:
            return

        try:
            self._sending.in_progress = True

            # Формируем JSON
            log_data = {
                "@timestamp": datetime.now().isoformat() + "Z",
                "level": record.levelname,
                "message": record.getMessage(),
                "service": self.service_name,
                "logger": record.name,
                "hostname": os.getenv("HOSTNAME", "unknown"),
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            }

            # Добавляем exception если есть
            if record.exc_info:
                log_data["exception"] = self.format(record)

            # Добавляем extra поля
            for key, value in record.__dict__.items():
                if key not in {'name', 'msg', 'args', 'created', 'filename', 'funcName',
                               'levelname', 'levelno', 'lineno', 'module', 'msecs',
                               'pathname', 'process', 'processName', 'relativeCreated',
                               'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                               'getMessage', 'taskName'} and not key.startswith('_'):
                    try:
                        str(value)  # Проверка сериализации
                        log_data[key] = value
                    except:
                        pass

            # Отправляем в Elasticsearch БЕЗ логирования
            self.es.index(
                index=f"logs-{self.service_name}-{datetime.now().strftime('%Y.%m.%d')}",
                document=log_data,
                refresh=False
            )

        except Exception:
            pass  # Молча игнорируем ошибки
        finally:
            self._sending.in_progress = False


def setup_elastic_logging_global(service_name="fast-api", delay_seconds=5):
    """
    Настраивает Elasticsearch хендлер для ВСЕХ логгеров
    """

    # ВАЖНО: Отключаем логи ДО всего остального
    for logger_name in [
        'elasticsearch',
        'elasticsearch.trace',
        'elastic_transport',
        'elastic_transport.transport',
        'elastic_transport.node',
        'elastic_transport.node_pool',
        'urllib3',
        'urllib3.connectionpool',
        'urllib3.util',
        'urllib3.util.retry'
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
        logging.getLogger(logger_name).propagate = False

    if delay_seconds > 0:
        print(f"⏳ Ожидаем {delay_seconds} секунд перед подключением к Elasticsearch...")
        time.sleep(delay_seconds)

    root_logger = logging.getLogger()

    # Проверяем, не добавлен ли уже
    for handler in root_logger.handlers:
        if isinstance(handler, ElasticsearchHandler):
            print(f"⚠️ Elasticsearch handler уже добавлен")
            return root_logger

    # Создаем хендлер
    es_handler = ElasticsearchHandler(service_name=service_name)
    es_handler.setLevel(logging.INFO)

    # Создаем фильтр для исключения системных логов
    class SystemLogFilter(logging.Filter):
        def filter(self, record):
            # Исключаем системные логгеры
            return not any(record.name.startswith(ignored)
                           for ignored in ElasticsearchHandler.IGNORED_LOGGERS)

    es_handler.addFilter(SystemLogFilter())

    # Добавляем к корневому логгеру
    root_logger.addHandler(es_handler)

    print(f"✅ Elasticsearch хендлер добавлен глобально для сервиса '{service_name}'")
    return root_logger


# Синглтон для управления единственным экземпляром
class ElasticLoggerManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, service_name="fast-api", delay_seconds=5):
        """Инициализация Elasticsearch логирования (вызывать только один раз)"""
        if not self._initialized:
            setup_elastic_logging_global(service_name, delay_seconds)
            self._initialized = True
            return True
        return False

    def get_logger(self, name):
        """Получить логгер (будет автоматически писать в ES если инициализирован)"""
        return logging.getLogger(name)