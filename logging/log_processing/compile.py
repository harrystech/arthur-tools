"""
Compile log records from multiple files, local or remote on S3.

The "interactive" use is really more of a demonstration  / debugging utility.
The real juice comes from milking lambda connected to S3 events so that any
log file posted by the data pipelines is automatically drained into an
Elasticsearch Service pool. That should quench your thirst for log fluids.
"""

import io
import gzip
import sys
import urllib.parse
from functools import partial

import boto3

# Note that relative imports don't work with Lambda
from log_processing import parse


def load_records(sources):
    """
    Load log records from a list of sources (as if they had all come from a single source.)

    If a source is called "examples", the built-in examples are added.
    If a source starts with "s3://", then we'll try to find it in S3.
    Otherwise, the file by the name of the source had better exist locally.
    """
    for source in sources:
        if source == "examples":
            for record in parse.create_example_records():
                yield record
        else:
            if source.startswith("s3://"):
                for record in _load_records_using(_load_remote_content, source):
                    yield record
            else:
                for record in _load_records_using(_load_local_content, source):
                    yield record


def _load_records_using(content_reader, content_location):
    print("Parsing '{}'".format(content_location))
    lines = content_reader(content_location)
    log_parser = parse.LogParser(content_location)
    return log_parser.split_log_lines(lines)


def _load_local_content(filename):
    if filename.endswith(".gz"):
        with gzip.open(filename, 'rb') as f:
            lines = f.read().decode()
    else:
        with open(filename, 'r') as f:
            lines = f.read()
    return lines


def _load_remote_content(uri):
    split_result = urllib.parse.urlsplit(uri)
    if split_result.scheme != "s3":
        raise ValueError("scheme {} not supported".format(split_result.scheme))
    bucket_name, object_key = split_result.netloc, split_result.path.lstrip('/')
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    obj = bucket.Object(object_key)
    response = obj.get()['Body']
    if object_key.endswith(".gz"):
        stream = io.BytesIO(response.read())
        lines = gzip.GzipFile(fileobj=stream).read().decode()
    else:
        lines = response.read().decode()
    return lines


def filter_record(query, record):
    for key in ("etl_id", "log_level", "message"):
        if query in record[key]:
            return True
    return False


def main():
    if len(sys.argv) < 3:
        print("Usage: {} QUERY LOGFILE [LOGFILE ...]".format(sys.argv[0]))
        exit(1)
    query = str(sys.argv[1])
    processed = load_records(sys.argv[2:])
    matched = filter(partial(filter_record, query), processed)
    for record in sorted(matched, key=lambda r: r["datetime"]["epoch_time_in_millis"]):
        print("{0[@timestamp]} {0[etl_id]} {0[log_level]} {0[message]}".format(record))


if __name__ == "__main__":
    main()
