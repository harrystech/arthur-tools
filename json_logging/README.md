# JSON-formatted Logging

The package `json_logging` supports regular Python logging to be formatted as
JSON which makes it much easier to post-process, for example, by loading log
lines into an Elasticsearch cluster or by defining metrics in CloudWatch.

## Fields

These are the default fields that are logged:

Name | Example value | Notes
----|----|----
`aws_request_id` | | Request id when executing a function in AWS
`gmtime` | `2020-08-02T15:24:59.154Z` | Timestamp in RFC3339 format
`log_level` | `INFO` | Log level as string
`log_severity` | 20 | Log level as number
`logger` | `mod.func` | Name of the logger, usually set using `__name__`
`message` | `Doing work` | Log message
`process.id` | 75478 | Id of the process running the application
`process.name` | `MainProcess` | Name of the process running the application
`source.filename` | `example.py` | File where we logged
`source.function` | `do_something` | Name of the function within which we logged
`source.line_number` | 42 | Where in the source file we logged
`source.module` | `example` | Name of the module (which may be less unique than the filename)
`source.pathname` | `python/src/example.py` | Location of the source file in the package
`thread.name` | `MainThread` | Name of the thread
`timestamp` | 1596381899154 | Epoch milliseconds

## Installation

Add this line to your `requirements.txt` file:
```text
git+https://github.com/harrystech/arthur-tools.git#subdirectory=json_logging&egg=json-logging
```

## Usage

### General use in applications

Add something like this to your code:
```python
import json_logging

json_logging.configure_logging()
logger = json_logging.getLogger(__name__)
logger.info("Hello World!")
```

### Use for Lambda functions

```python
import json_logging

json_logging.configure_logging()
logger = json_logging.getLogger(__name__)


def handle_event(event, context):
    json_logging.update_context(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name,
        function_version=context.function_version,
        invoked_function_arn=context.invoked_function_arn,
        log_stream_name=context.log_stream_name,
    )
    logger.info(f"Starting {__name__}", extra={"event": event})
```

### "Library" code

Outside the main module where you configure the logger, the pattern is:
```python
import json_logging

logger = json_logging.getLogger(__name__)
logger.addHandler(json_logging.NullHandler())
```

### "Extra" information

You can send additional information into the log record using the `extra` kwarg, which
avoids having to process the message later:
```python
logger.info(f"Finished processing {num_count} file(s)", extra={"file_count": num_count})
```

#### Context wrapper

Log an exception along with a strack trace like so:
```python
with json_logging.log_stack_trace(logger):
    do_something_dangerous()
```
(Note that this doesn't "catch" the exception.)

## Development

You can also test the installation by calling `pip` directly. (You should
probably do so inside a Docker container or using a virtual environment.)
```shell script
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade 'git+https://github.com/harrystech/arthur-tools.git@next#subdirectory=json_logging&egg=json-logging'
```

### Running unit tests

```shell script
cd json_logging
python3 -m unittest discover tests
python3 json_logging/__init__.py
```
