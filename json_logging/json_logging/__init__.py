"""
Enable logging (from Lambda functions) in JSON format which makes post-processing much easier.

Since we assume this will be used by Lambda functions, we also add the request id in log lines.
"""

import json
import logging
import logging.config
import sys
import traceback
from contextlib import ContextDecorator
from datetime import datetime, timezone
from logging import NullHandler  # noqa: F401
from typing import Any, Dict, List, Optional, Tuple, Union


class ContextFilter(logging.Filter):
    """
    Logging Filter class that adds contextual information to log records.

    We assume there will be only one instance of this filter for any runtime which
    means that we will store some values with the class, not the instances.
    """

    _context: Dict[str, Optional[str]] = {
        "aws_request_id": None,
        "correlation_id": None,
        "function_name": None,
        "function_version": None,
        "invoked_function_arn": None,
        "log_group_name": None,
        "log_stream_name": None,
        "request_id": None,
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Modify record in place for additional fields, then return True to continue processing."""
        for field, value in self._context.items():
            if value is not None:
                setattr(record, field, value)
        return True

    @classmethod
    def update_from_lambda_context(cls, context: Any) -> None:
        """Update fields stored in the global context filter based on attributes of the context."""
        for field, value in cls._context.items():
            cls._context[field] = getattr(context, field, value)

    @classmethod
    def update_context(cls, **kwargs: Optional[str]) -> None:
        """
        Update any of the fields stored in the global context filter.

        Note that trying to set a field that's not been defined raises a ValueError.
        Setting a field to None removes it from the output.
        """
        for field, value in kwargs.items():
            if field in cls._context:
                cls._context[field] = value
            else:
                raise ValueError(f"unexpected field: '{field}'")


class DefaultJsonFormat(json.JSONEncoder):
    """Default to using 'str()' except for dates which are ISO 8601."""

    def default(self, obj: Any) -> str:
        if isinstance(obj, datetime):
            s = obj.isoformat(timespec="milliseconds")
            if s.endswith("+00:00"):
                # Make 99% of our timestamps easier to read by replacing the time offset with "Z".
                return s[:-6] + "Z"
            return s
        else:
            return str(obj)


class JsonFormatter(logging.Formatter):
    """
    Format the message to be easily reverted into an object by using JSON format.

    Notes:
        * The "format" is ignored since we convert based on available info.
        * The timestamps are in UTC.

    This format of "gmtime" is compatible with "strict_date_time" in Elasticsearch,
    (as "yyyy-MM-dd'T'HH:mm:ss.SSSZZ") and other log collection tools.
    """

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
        "log_group_name": "cwl.log_group_name",
        "log_stream_name": "cwl.log_stream_name",
        # LogRecord attributes which we want to suppress or rewrite ourselves:
        "args": None,
        "created": None,
        "msecs": None,
        "msg": None,
        "relativeCreated": None,
        "thread": None,
    }

    # Use "set_output_format()" to change these values.
    output_format = "compact"
    output_fields: Optional[List[str]] = None

    @property
    def indent(self) -> Optional[str]:
        return {"compact": None, "pretty": "    "}[self.output_format]

    @property
    def separators(self) -> Tuple[str, str]:
        return {"compact": (",", ":"), "pretty": (",", ": ")}[self.output_format]

    def format(self, record: logging.LogRecord) -> str:
        """Format log record by creating a JSON-format in a string."""
        assembled = {}
        for attr, value in record.__dict__.items():
            if value is None:
                continue
            if attr in self.attribute_mapping:
                new_name = self.attribute_mapping[attr]
                if new_name is not None:
                    assembled[new_name] = value
                continue
            # This lets anything, I mean anything, from "extra={}" slip through.
            assembled[attr] = value

        # The "message" is added here so an accidentally specified message in the extra kwargs
        # is ignored.
        assembled["message"] = record.getMessage()
        # We show elapsed milliseconds as int, not float.
        assembled["elapsed_ms"] = int(record.relativeCreated)
        # Finally, always add a timestamp as epoch msecs and in a human readable format.
        # (Go to https://www.epochconverter.com/ to convert the timestamp in milliseconds.)
        assembled["timestamp"] = int(record.created * 1000.0)
        assembled["gmtime"] = datetime.fromtimestamp(record.created, timezone.utc)
        # Note that we show only the values of fields when specific fields were requested.
        if self.output_fields is not None:
            assembled = [assembled[field] for field in self.output_fields]  # type: ignore
        return json.dumps(
            assembled,
            cls=DefaultJsonFormat,
            indent=self.indent,
            separators=self.separators,
            sort_keys=True,
        )


# We don't create this dict earlier so that we can use the classes (instead of their names
# as strings).
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


def configure_logging(level: Union[int, str] = "INFO") -> None:
    """Configure logging module to use JSON formatter for logs."""
    logging.config.dictConfig(LOGGING_STREAM_CONFIG)
    logging.captureWarnings(True)
    logging.root.setLevel(level)


# Just for developer convenience -- this avoids having too many imports of "logging" packages.
def getLogger(name: str = None) -> logging.Logger:
    return logging.getLogger(name)


def set_output_format(
    pretty: bool = False, pretty_if_tty: bool = False, terse: bool = False
) -> None:
    if pretty or (pretty_if_tty and sys.stdout.isatty()):
        JsonFormatter.output_format = "pretty"
    else:
        JsonFormatter.output_format = "compact"
    if terse:
        JsonFormatter.output_fields = ["gmtime", "log_level", "message"]
    else:
        JsonFormatter.output_fields = None


def update_from_lambda_context(context: Any) -> None:
    """Update values in the logging context from the context of a AWS Lambda function."""
    ContextFilter.update_from_lambda_context(context)


def update_context(**kwargs: Optional[str]) -> None:
    """Update values in the logging context to be included with every log record."""
    ContextFilter.update_context(**kwargs)


class log_stack_trace(ContextDecorator):
    """This context enables logging a stacktrace automatically when an exception occurs."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def __enter__(self) -> "log_stack_trace":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        if exc_type:
            tb = traceback.TracebackException(exc_type, exc_val, exc_tb)
            message = next(tb.format_exception_only()).strip()
            stack_trace_lines = ("".join(tb.format())).splitlines()
            self._logger.error(message, extra={"stack_trace": stack_trace_lines})
        return None
