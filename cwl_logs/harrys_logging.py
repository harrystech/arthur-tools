import json
import logging, logging.config
import os
import time


class RequestIdFilter(logging.Filter):
    """
    We use this class to add key-value pairs to the log record json
    """
    environment = "UNKNOWN"
    process_id = "NONE"
    request_uuid = "NONE"
    request_number = 0
    request_uuid_unique = "NONE"
    request_status = "NONE"
    entity_name = "NONE"
    function_name = "NONE"
    function_version = "NONE"
    error_type = "NONE"

    def filter(self, record):
        record.environment = self.environment
        record.process_id = self.process_id
        record.request_uuid = self.request_uuid
        record.request_number = self.request_number
        record.request_uuid_unique = self.request_uuid_unique
        record.request_status = self.request_status
        record.entity_name = self.entity_name
        record.function_name = self.function_name
        record.function_version = self.function_version
        record.error_type = self.error_type
        return True


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


def get_format_str(format_type):
    formats = {
        'json': '{'
                '"_timestamp_": "%(asctime)s", '
                '"log_level": "%(levelname)s", '
                '"function_name": "%(function_name)s", '
                '"function_version": "%(function_version)s", '
                '"request_uuid": "%(request_uuid)s", '
                '"request_number": "%(request_number)s", '
                '"request_uuid_unique": "%(request_uuid_unique)s", '
                '"process_id": "%(process_id)s", '
                '"file_name": "%(filename)s:%(lineno)s", '
                '"request_status": "%(request_status)s", '
                '"entity_name": "%(entity_name)s", '
                '"error_type": "%(error_type)s", '
                '"message": "%(message)s" }',
        'flat': '%(asctime)s|%(levelname)s|%(filename)s:%(lineno)s|%(entity_name)s|%(message)s'
    }
    return formats[format_type]


def setup_logging(default_level=logging.INFO, log_prefix='', format_type='json'):
    """Setup logging configuration """
    env_name = os.getenv('ENV_NAME', 'UKNOWN')
    RequestIdFilter.environment = env_name
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        'formatters': {
            'utc': {
                '()': UTCFormatter,
                'format': get_format_str(format_type=format_type)
            }
        },
        "filters": {
            "request_id": {"()": RequestIdFilter}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "utc",
                "stream": "ext://sys.stdout",
                "filters": ["request_id"]
            }
        },
        "root": {
            "level": "INFO",
            "handlers": [
                "console"
            ]
        }
    }
    logging.config.dictConfig(log_config)
    return


def set_log_record_field(environment=None, process_id=None, request_uuid=None, request_number=None,
                         request_status=None, entity_name=None, function_name=None, function_version=None,
                         error_type=None):
    RequestIdFilter.environment = environment or RequestIdFilter.environment
    RequestIdFilter.request_uuid = request_uuid or RequestIdFilter.request_uuid
    RequestIdFilter.request_number = request_number or RequestIdFilter.request_number
    RequestIdFilter.request_uuid_unique = f"{RequestIdFilter.request_uuid}_{str(RequestIdFilter.request_number)}"
    RequestIdFilter.process_id = process_id or RequestIdFilter.process_id
    RequestIdFilter.request_status = request_status or RequestIdFilter.request_status
    RequestIdFilter.entity_name = entity_name or RequestIdFilter.entity_name
    RequestIdFilter.function_name = function_name or RequestIdFilter.function_name
    RequestIdFilter.function_version = function_version or RequestIdFilter.function_version
    RequestIdFilter.error_type = error_type or RequestIdFilter.error_type
    return


def reset_log_record_fields( ):
    RequestIdFilter.environment = "NONE"
    RequestIdFilter.request_uuid = "NONE"
    RequestIdFilter.request_number = 0
    RequestIdFilter.request_uuid_unique = "NONE"
    RequestIdFilter.process_id = "NONE"
    RequestIdFilter.request_status = "NONE"
    RequestIdFilter.entity_name = "NONE"
    RequestIdFilter.function_name = "NONE"
    RequestIdFilter.function_version = "NONE"
    RequestIdFilter.error_type = "NONE"
    return


def unset_log_record_fields(field_list: list):
    for f in field_list:
        if f == "request_number":
            setattr(RequestIdFilter, f, 0)
        else:
            setattr(RequestIdFilter, f, "NONE")


def safe_json(obj_to_pretty: object, indent=False):
    """ printing dictionaries to the logs is HARD. this pretty print method lets us do it in a way that is safe
    for our particular use case """
    if indent:
        return json.dumps(obj_to_pretty, default=str, sort_keys=True, indent=2)
    else:
        safe_str = json.dumps(obj_to_pretty, default=str, sort_keys=True)
        safe_str = safe_str.replace("{", '\{').replace("}", '\}').replace('"', '\\"')
        return safe_str


def safe_string(bad_str: str):
    return bad_str.replace("\n", '').replace("\t", '').replace(":", '-')


