"""
Access to shared settings and managing indices
"""

import argparse
import datetime
import logging
import time
from functools import lru_cache

import boto3
import elasticsearch
import requests_aws4auth

from log_processing import parse

logger = logging.getLogger(__name__)

LOG_INDEX_PATTERN = "dw-logs-*"
LOG_INDEX_TEMPLATE_NAME = LOG_INDEX_PATTERN.replace("-*", "-template")
OLDEST_INDEX_IN_DAYS = 380

ES_ENDPOINT_BY_ENV_TYPE = "/DW-ETL/ES-By-Env-Type/{env_type}"
ES_ENDPOINT_BY_BUCKET = "/DW-ETL/ES-By-Bucket/{bucket_name}"


@lru_cache()
def get_index_name(date=None):
    """Return name of index for current date (or specified date) with granularity of one month."""
    if date is None:
        instant = datetime.date.today()
    elif isinstance(date, datetime.date):
        instant = date
    else:
        instant = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    return instant.strftime(LOG_INDEX_PATTERN.replace("-*", "-%Y-%m"))


def set_es_endpoint(env_type, bucket_name, endpoint):
    """Set SSM parameters so that lambdas can find the appropriate Elasticsearch cluster."""
    client = boto3.client("ssm")
    for parameter in (ES_ENDPOINT_BY_ENV_TYPE, ES_ENDPOINT_BY_BUCKET):
        name = parameter.format(env_type=env_type, bucket_name=bucket_name)
        logger.info(f"Setting parameter '{name}'")
        client.put_parameter(
            Name=name,
            Description="Value of 'host:port' of Elasticsearch cluster for log processing",
            Value=endpoint,
            Type="String",
            Overwrite=True,
        )
        client.add_tags_to_resource(
            ResourceType="Parameter",
            ResourceId=name,
            Tags=[{"Key": "user:project", "Value": "data-warehouse"}],
        )


def get_es_endpoint(env_type=None, bucket_name=None):
    """
    Get value of SSM parameters based either on the environment or the bucket.

    (The bucket should presumably have log files).
    """
    if env_type is not None:
        name = ES_ENDPOINT_BY_ENV_TYPE.format(env_type=env_type)
    elif bucket_name is not None:
        name = ES_ENDPOINT_BY_BUCKET.format(bucket_name=bucket_name)
    else:
        raise ValueError("one of 'env_type' or 'bucket_name' must be not None")
    client = boto3.client("ssm")
    logger.info(f"Looking up parameter '{name}'")
    response = client.get_parameter(Name=name, WithDecryption=False)
    es_endpoint = response["Parameter"]["Value"]
    host, port = es_endpoint.rsplit(":", 1)
    return host, int(port)


def _aws_auth():
    # https://github.com/sam-washington/requests-aws4auth/pull/2
    session = boto3.Session()
    logger.info(
        f"Retrieving credentials "
        f"(profile_name={session.profile_name}, region_name={session.region_name})",
    )
    credentials = session.get_credentials()
    aws4auth = requests_aws4auth.AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        session.region_name,
        "es",
        session_token=credentials.token,
    )

    def wrapped_aws4auth(request):
        return aws4auth(request)

    return wrapped_aws4auth


def connect_to_es(host, port, use_auth=False):
    """
    Return client that's connected to an Elasticsearch cluster.

    Unless running from authorized IP, set use_auth to True so that credentials are based on role.
    """
    if use_auth:
        http_auth = _aws_auth()
    else:
        http_auth = None
    es = elasticsearch.Elasticsearch(
        hosts=[{"host": host, "port": port}],
        use_ssl=True,
        verify_certs=True,
        connection_class=elasticsearch.connection.RequestsHttpConnection,
        http_auth=http_auth,
        send_get_body_as="POST",
    )
    return es


def exists_index_template(client):
    return client.indices.exists_template(LOG_INDEX_TEMPLATE_NAME)


def put_index_template(client):
    version = int(time.time())
    body = {
        "template": LOG_INDEX_PATTERN,
        "version": version,
        "settings": {"number_of_shards": 2, "number_of_replicas": 1},
        "mappings": {"properties": parse.LogRecord.index_properties()},
    }
    logger.info(f"Updating index template '{LOG_INDEX_TEMPLATE_NAME}' (version={version})")
    client.indices.put_template(LOG_INDEX_TEMPLATE_NAME, body)


def get_current_indices(client):
    """Return set of indices currently used in the cluster."""
    logger.info(f"Looking for indices matching '{LOG_INDEX_PATTERN}'")
    response = client.indices.get(index=LOG_INDEX_PATTERN, allow_no_indices=True)
    return frozenset(response[index]["settings"]["index"]["provided_name"] for index in response)


def get_allowable_indices():
    """Return set of indices expected in use given our retention period."""
    today = datetime.datetime.utcnow()
    return frozenset(
        get_index_name(today - datetime.timedelta(days=days))
        for days in range(0, OLDEST_INDEX_IN_DAYS)
    )


def build_parser():
    parser = argparse.ArgumentParser(description="Configure log processing")
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers()
    # Retrieve current configuration
    get_config_parser = subparsers.add_parser("get_endpoint", help="get endpoint by env type")
    get_config_parser.add_argument("env_type", help="environment type (like 'dev' or 'prod')")
    get_config_parser.set_defaults(func=sub_get_endpoint)
    # Set new configuration
    set_config_parser = subparsers.add_parser(
        "set_endpoint", help="set endpoint for env type and bucket"
    )
    set_config_parser.add_argument("env_type", help="environment type (like 'dev' or 'prod')")
    set_config_parser.add_argument("bucket_name", help="name of S3 bucket with log files")
    set_config_parser.add_argument(
        "endpoint", help="endpoint for Elasticsearch service (host:port)"
    )
    set_config_parser.set_defaults(func=sub_set_endpoint)
    # Upload (new) index template
    put_index_template_parser = subparsers.add_parser(
        "put_index_template", help="upload (new) index template"
    )
    put_index_template_parser.add_argument(
        "env_type", help="environment type (like 'dev' or 'prod')"
    )
    put_index_template_parser.set_defaults(func=sub_put_index_template)
    # Get list of current indices matching our pattern
    get_indices_parser = subparsers.add_parser("get_indices", help="get current indices")
    get_indices_parser.add_argument("env_type", help="environment type (like 'dev' or 'prod')")
    get_indices_parser.set_defaults(func=sub_get_indices)
    # Delete indices for records older than a year
    delete_stale_indices_parser = subparsers.add_parser(
        "delete_stale_indices", help="delete older indices"
    )
    delete_stale_indices_parser.add_argument(
        "env_type", help="environment type (like 'dev' or 'prod')"
    )
    delete_stale_indices_parser.set_defaults(func=sub_delete_stale_indices)
    return parser


def sub_get_endpoint(args):
    host, port = get_es_endpoint(env_type=args.env_type)
    logger.info(f"Found ES domain at '{host}:{port}'")


def sub_set_endpoint(args):
    set_es_endpoint(args.env_type, args.bucket_name, args.endpoint)


def sub_put_index_template(args):
    host, port = get_es_endpoint(env_type=args.env_type)
    es = connect_to_es(host, port, use_auth=False)
    put_index_template(es)


def sub_get_indices(args):
    host, port = get_es_endpoint(env_type=args.env_type)
    es = connect_to_es(host, port, use_auth=False)
    for name in reversed(sorted(get_current_indices(es))):
        print("   ", name)


def sub_delete_stale_indices(args):
    host, port = get_es_endpoint(env_type=args.env_type)
    es = connect_to_es(host, port, use_auth=False)
    stale = get_current_indices(es).difference(get_allowable_indices())
    if not stale:
        print(f"Found no indices older than {OLDEST_INDEX_IN_DAYS} days.")
        return
    for name in reversed(sorted(stale)):
        print("** ", name)
    print(f"Indices marked '**' are older than {OLDEST_INDEX_IN_DAYS} days.")
    try:
        proceed = input("Proceed to delete old indices? (y/[n]) ")
    except EOFError:
        proceed = "n"
    if proceed.lower() in ("y", "yes"):
        print("Ok, deleting old indices.")
        es.indices.delete(",".join(sorted(stale)))


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.func:
        parser.print_usage()
    else:
        args.func(args)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
