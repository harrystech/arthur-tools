
#### Current Log Structure:
Currently using the following common set of fields across applications/lambdas:

###### STANDARD PYTHON FIELDS:
    timestamp
    log_level
    file_name
    message

###### CUSTOM FIELDS:
    environment                 [dev/prod/core-dev etc]
    process_id                  [unique process identifier e.g. lambda uuid]
    request_uuid                [same across applications/lambdas for a request]
    request_number              [when LOOPING over a batch e.g. 20 kinesis messages]
    request_uuid_unique         [concat request_uuid and request_number]
    request_status              [e.g. START, DECODE, POST, SUCCESS/FAIL]
    entity_name                 [usually a table_name but can be a filename, stream_name]
    function_name               [lambda or applciation name]
    function_version            [lambda or application version]
    error_type                  [when logging exceptions, please attach this - useful to classify/group errors]
