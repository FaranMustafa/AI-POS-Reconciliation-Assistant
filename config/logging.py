import logging


LOGGER_NAME = "pos_reconciliation"
RESERVED_LOG_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


def get_app_logger():
    return logging.getLogger(LOGGER_NAME)


def build_log_extra(event: str, **context):
    safe_context = {}
    for key, value in context.items():
        safe_key = f"context_{key}" if key in RESERVED_LOG_RECORD_KEYS else key
        safe_context[safe_key] = value
    return {"event": event, **safe_context}


def log_event(event: str, message: str, **context):
    get_app_logger().info(f"{event}: {message}", extra=build_log_extra(event, **context))
