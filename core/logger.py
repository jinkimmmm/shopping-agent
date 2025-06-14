"""로깅 설정 및 관리"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import settings


def setup_logging() -> None:
    """애플리케이션 로깅 설정"""
    
    # 로그 디렉토리 생성
    log_file_path = Path(settings.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 로깅 설정
    if settings.log_format.lower() == "json":
        _setup_structured_logging()
    else:
        _setup_standard_logging()
    
    # 루트 로거 레벨 설정
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.INFO)
    logging.getLogger("qdrant_client").setLevel(logging.INFO)


def _setup_structured_logging() -> None:
    """구조화된 로깅 설정 (JSON 형식)"""
    
    # structlog 설정
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 표준 로깅 설정
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": settings.log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "root": {
            "level": settings.log_level.upper(),
            "handlers": ["console", "file"]
        }
    }
    
    logging.config.dictConfig(logging_config)


def _setup_standard_logging() -> None:
    """표준 로깅 설정 (Rich 형식)"""
    
    console = Console()
    
    # Rich 핸들러 설정
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True
    )
    
    # 파일 핸들러 설정
    file_handler = logging.handlers.RotatingFileHandler(
        settings.log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    
    # 포매터 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))


def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    if settings.log_format.lower() == "json":
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


class LoggerMixin:
    """로거 믹스인 클래스"""
    
    @property
    def logger(self) -> logging.Logger:
        """클래스별 로거 반환"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """함수 호출 로깅 데코레이터"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(
            f"함수 호출: {func.__name__}",
            extra={
                "function": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_count": len(kwargs)
            }
        )
        try:
            result = func(*args, **kwargs)
            logger.info(
                f"함수 완료: {func.__name__}",
                extra={"function": func.__name__, "success": True}
            )
            return result
        except Exception as e:
            logger.error(
                f"함수 오류: {func.__name__}",
                extra={
                    "function": func.__name__,
                    "error": str(e),
                    "success": False
                },
                exc_info=True
            )
            raise
    return wrapper