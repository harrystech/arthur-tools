LOG_RECORD_MAPPINGS = {
    "properties": {
        "application_name": {"type": "keyword"},
        "environment": {"type": "keyword"},
        "logfile": {
            "type": "keyword",
        },
        "data_pipeline": {
            "properties": {
                "id": {"type": "keyword"},
                "component": {"type": "keyword"},
                "instance": {"type": "keyword"},
                "attempt": {"type": "keyword"}
            }
        },
        "emr_cluster": {
            "properties": {
                "id": {"type": "keyword"},
                "step_id": {"type": "keyword"}
            }
        },
        "@timestamp": {"type": "date", "format": "strict_date_optional_time"},  # generic ISO datetime parser
        "datetime": {
            "properties": {
                "epoch_time_in_millis": {"type": "long"},
                "date": {"type": "date", "format": "strict_date"},  # used to select index during upload
                "year": {"type": "integer"},
                "month": {"type": "integer"},
                "day": {"type": "integer"},
                "day_of_week": {"type": "integer"},
                "hour": {"type": "integer"},
                "minute": {"type": "integer"},
                "second": {"type": "integer"}
            },
        },
        "etl_id": {"type": "keyword"},
        "log_level": {"type": "keyword"},
        "logger": {
            "type": "text",
            "analyzer": "simple",
            "fields": {
                "name": {
                    "type": "keyword"
                }
            }
        },
        "thread_name": {"type": "keyword"},
        "source_code": {
            "properties": {
                "filename": {"type": "text"},
                "line_number": {"type": "integer"},
            }
        },
        "message": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "raw": {
                    "type": "keyword"
                },
                "english": {
                    "type": "text",
                    "analyzer": "english"
                }
            }
        },
        "monitor": {
            "properties": {
                "monitor_id": {"type": "keyword"},
                "step": {"type": "keyword"},
                "event": {"type": "keyword"},
                "target": {"type": "keyword"},
                "elapsed": {"type": "float"},
                "rowcount": {"type": "long"},
                "error_codes": {"type": "text"}
            }
        },
        "parser": {
            "properties": {
                "start_pos": {"type": "long"},
                "end_pos": {"type": "long"},
                "chars": {"type": "long"}
            },
        },
        # These last properties are only used by the Lambda handler:
        "lambda_name": {"type": "keyword"},
        "lambda_version": {"type": "keyword"},
        "context": {
            "properties": {
                "remaining_time_in_millis": {"type": "long"}
            }
        },
        "original_logfile": {
            "type": "keyword",
        }
    }
}

