"""
Enable logging (from Lambda functions) in JSON format which makes post-processing much easier.

Since we assume this will be used by Lambda functions, we also add the request id in log lines.
"""

import json
import logging
import logging.config
import time
import traceback
from contextlib import ContextDecorator
from logging import NullHandler


# Just for developer convenience -- this avoids having too many imports of "logging" packages.
def getLogger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class ContextFilter(logging.Filter):
    """
    Logging Filter class that adds contextual information to log records.

    We assume there will be only one instance of this filter for any runtime which
    means that we will store some values with the class, not the instances.
    """

    _context = {
        "aws_request_id": "UNKNOWN",  # mypy stumbles on all values being None
        "function_name": None,
        "function_version": None,
        "invoked_function_arn": None,
        "log_group_name": None,
        "log_stream_name": None,
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Modify record in place for additional fields, then return True to continue processing."""
        for field, value in self._context.items():
            if value is not None:
                setattr(record, field, value)
        return True

    @classmethod
    def update_context(cls, **kwargs: str) -> None:
        """
        Update any of the fields stored in the (global) context filter.

        Note that trying to set a field that's not been defined raises a ValueError.
        """
        for field, value in kwargs.items():
            if field in cls._context:
                cls._context[field] = value
            else:
                raise ValueError(f"unexpected field: '{field}'")


class JsonFormatter(logging.Formatter):
    """
    Format the message to be easily reverted into an object by using JSON format.

    Notes:
        * The "format" is ignored since we convert based on available info.
        * The timestamps are in UTC.
    """

    # This format is compatible with "strict_date_time" in Elasticsearch:
    # yyyy-MM-dd'T'HH:mm:ss.SSSZZ
    converter = time.gmtime
    default_time_format = "%Y-%m-%dT%H:%M:%SZ"
    default_msec_format = "%.19s.%03dZ"

    attribute_mapping = {
        # LogRecord attributes for which we want new names:
        "filename": "source.filename",
        "funcName": "source.function",
        "levelname": "log_level",
        "levelno": "log_severity",
        "lineno": "source.line_number",
        "module": "source.module",
        "name": "logger",
        "pathname": "source.pathname",
        "process": "process.id",
        "processName": "process.name",
        "threadName": "thread.name",
        # Common context attributes which we want to rename:
        "function_name": "lambda.function_name",
        "function_version": "lambda.function_version",
        "invoked_function_arn": "lambda.invoked_function_arn",
        "log_stream_name": "cwl.log_stream_name",
        # LogRecord attributes which we want to suppress:
        "args": None,
        "created": None,
        "msecs": None,
        "msg": None,
        "relativeCreated": None,
        "thread": None,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record by creating a JSON-format in a string."""
        data = {}
        for attr, value in record.__dict__.items():
            if value is None:
                continue
            if attr in self.attribute_mapping:
                new_name = self.attribute_mapping[attr]
                if new_name is not None:
                    data[new_name] = value
            else:
                data[attr] = value
        # The "message" is added last so an accidentally specified message in the extra kwargs
        # is ignored.
        data["message"] = record.getMessage()
        # Finally, always add a timestamp as epoch msecs and in a human readable format.
        # (Go to https://www.epochconverter.com/ to convert the timestamp in milliseconds.)
        data["timestamp"] = int(record.created * 1000.0)
        data["gmtime"] = self.formatTime(record)
        return json.dumps(data, default=str, separators=(",", ":"), sort_keys=True)


# We don't create the config dict until here so that we can use the classes
# (instead of class names in strings).
LOGGING_STREAM_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json_formatter": {"()": JsonFormatter}},
    "filters": {"context_filter": {"()": ContextFilter}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "json_formatter",
            "filters": ["context_filter"],
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        # Loggers from packages that we use and want to be less noisy:
        "botocore": {
            "qualname": "botocore",
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": 0,
        },
        "elasticsearch": {
            "qualname": "elasticsearch",
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": 0,
        },
        "urllib3": {
            "qualname": "urllib3",
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": 0,
        },
    },
}


def configure_logging() -> None:
    logging.config.dictConfig(LOGGING_STREAM_CONFIG)


def update_context(**kwargs: str) -> None:
    ContextFilter.update_context(**kwargs)


class log_stack_trace(ContextDecorator):
    """This context enables logging a stacktrace automatically when an exception occurs."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def __enter__(self) -> "log_stack_trace":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        if exc_type:
            self._logger.error(
                f"Exception: {exc_val!r}",
                extra={"stack_trace": traceback.format_exception(exc_type, exc_val, exc_tb)},
            )
        return None


def main_test() -> None:
    configure_logging()
    logger = getLogger(__name__)
    logger.addHandler(NullHandler())

    update_context(aws_request_id="62E538E9-E9C5-415A-9771-6588F9A1A708")
    logging.info("Message at INFO level", extra={"planet": "earth"})

    num_count = 99
    logger.info(f"Finished counting {num_count} balloons", extra={"balloons": num_count})


if __name__ == "__main__":
    main_test()
