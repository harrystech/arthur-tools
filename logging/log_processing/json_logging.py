"""
Enable logging (from Lambdas) in JSON format which makes post-processing much easier.

Since we assume this will be used by Lambdas, we also add the request id in log lines.
"""

import json
import logging
import logging.config
import time


class ContextFilter(logging.Filter):
    """
    Logging Filter class that adds contextual information to log records.

    We assume there will be only one instance of this filter for any runtime which
    means that we will store some values with the class, not the instances.
    """

    _context = {
        "aws_request_id": None,
        "function_name": None,
        "function_version": None,
        "log_group_name": None,
        "log_stream_name": None,
    }

    def filter(self, record):
        """
        Modify record in place for additional fields, then return True to continue processing.
        """
        for field, value in self._context.items():
            if value is not None:
                setattr(record, field, value)
        return True

    @classmethod
    def update_context(cls, **kwargs):
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

    converter = time.gmtime

    attribute_mapping = {
        # LogRecord attributes for which we want new names:
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
        "log_stream_name": "cwl.log_stream_name",
        # LogRecord attributes which we want to suppress:
        "args": None,
        "created": None,
        "msecs": None,
        "msg": None,
        "relativeCreated": None,
        "thread": None,
    }

    def format(self, record):
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
        # The "message" is added last so an accidentally specified message in the extra kwargs is ignored.
        data["message"] = record.getMessage()
        return json.dumps(data, separators=(",", ":"), sort_keys=True)


# We don't create the config dict until here so that we can use the classes (instead of class names in strings).
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
    "loggers": {"botocore": {"qualname": "botocore", "handlers": ["console"], "level": "WARNING", "propagate": 0}},
}


def configure_logging():
    logging.config.dictConfig(LOGGING_STREAM_CONFIG)


# For convenience to avoid too many logging imports.
def getLogger(name):
    return logging.getLogger(name)


def update_context(**kwargs):
    ContextFilter.update_context(**kwargs)


if __name__ == "__main__":
    configure_logging()
    update_context(aws_request_id="62E538E9-E9C5-415A-9771-6588F9A1A708")

    logging.info("Message at INFO level", extra={"stuff": "more"})
