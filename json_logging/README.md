# JSON-formatted Logging

The package `json_logging` supports regular Python logging to be formatted as
JSON which makes it much easier to post-process, for example, by loading log
lines into an Elasticsearch cluster or by defining metrics in CloudWatch.

## Fields

These are the default fields that are logged:

Name | Example value | Notes
----|----|----
`aws_request_id` | `799ab13f-6d11-4f0d-853f-bad9fcad86c3` | Request id when executing a function in AWS
`elapsed_ms` | 24 | Elapsed time in milliseconds (since module was loaded)
`gmtime` | `2020-08-02T15:24:59.154Z` | Timestamp in RFC3339 format
`log_level` | `INFO` | Log level as string
`log_severity` | 20 | Log level as number which makes it easy to filter
`logger` | `mod.func` | Name of the logger, usually set using `__name__`
`message` | `Doing work` | Log message
`process.id` | 75478 | Id of the process running the application
`process.name` | `MainProcess` | Name of the process running the application
`source.filename` | `example.py` | File where we logged
`source.function` | `do_something` | Name of the function within which we logged
`source.line_number` | 42 | Where in the source file we logged
`source.module` | `example` | Name of the module (which may be less unique than the filename)
`source.pathname` | `python/src/example.py` | Location of the source file
`thread.name` | `MainThread` | Name of the running thread
`timestamp` | 1596381899154 | Epoch milliseconds

The fields were chosen to make it easy to collect the logs
into a system where we can search, trace and alert.

Either the `gmtime` or `timestamp` will allow sorting of log lines.

The output is normally one record per line. This allows treating the logs
as [JSONL](https://jsonlines.org/) and makes it easy to consume.

For development work, it is sometimes preferred to pretty-print the log,
similar to what you would see in CloudWatch logs when viewing log lines
that are JSON-formatted. Use `pretty=True` when configuring logging
to turn on this mode.
```shell
python3 example.py --pretty
```

## Installation

Add this line to your `requirements.txt` file to pull the `main` version:
```text
git+https://github.com/harrystech/arthur-tools.git#subdirectory=json_logging&egg=json-logging
```

To use a specific version or the latest developer version, change this to:
```text
git+https://github.com/harrystech/arthur-tools.git@next#subdirectory=json_logging&egg=json-logging
```

The syntax is described in the [documentation of `pip`](https://pip.pypa.io/en/stable/reference/pip_install/#vcs-support).

## Usage

### General Use In Applications

Add something like this to your code:
```python
import json_logging

json_logging.configure_logging()
logger = json_logging.getLogger(__name__)

json_logging.update_context(request_id='abcde-12345')
logger.info("Hello World!")
```

### Use For AWS Lambda Functions

The code example below
* configures logging in the module that is called by AWS Lambda
* uses the pretty-printed output but only in local testing
* copies the values from the context at runtime

```python
import json_logging

json_logging.configure_logging()
json_logging.set_output_format(pretty_if_tty=True)
logger = json_logging.getLogger(__name__)


def handle_event(event, context):
    json_logging.update_from_lambda_context(context)
    logger.info(f"Starting {__name__}", extra={"event": event})
```

### Library Code

Outside the main module where you configure the logger, the pattern is:
```python
import json_logging

logger = json_logging.getLogger(__name__)
logger.addHandler(json_logging.NullHandler())
```

### "Extra" Information

You can send additional information into the log record using the `extra` kwarg, which
avoids having to process the message later:
```python
logger.info(f"Finished processing {num_count} file(s)", extra={"file_count": num_count})
```

### Context Wrapper

Log an exception along with a stack trace like so:
```python
with json_logging.log_stack_trace(logger):
    do_something_dangerous()
```

Note that this doesn't "catch" the exception.

## Development

You can also test the installation by calling `pip` directly. (You should
probably do so inside a Docker container or using a virtual environment.)
```shell
cd json_logging
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade 'git+https://github.com/harrystech/arthur-tools.git@next#subdirectory=json_logging&egg=json-logging'
```

### Running unit tests

```shell
python3 -m pip install --upgrade --editable .

python3 -m unittest discover tests
```
