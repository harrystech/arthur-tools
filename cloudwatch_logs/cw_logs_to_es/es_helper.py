import json
import logging
import os

import boto3
import elasticsearch.helpers
import requests_aws4auth
from elasticsearch import Elasticsearch, RequestsHttpConnection

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

region_name = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
session = boto3.Session(region_name=region_name)


class ElasticsearchWrapper:
    def __init__(self, domain_name):
        host = ElasticsearchWrapper.find_es_host(domain_name)
        self.es = Elasticsearch(
            hosts=[{"host": host, "port": 443}],
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            http_auth=self._aws_auth(),
            http_compress=True,
            send_get_body_as="POST",
        )
        logger.info(f"Cluster info: {self.es.info()}")

    @staticmethod
    def find_es_host(domain_name):
        client = session.client("es")
        response = client.describe_elasticsearch_domain(DomainName=domain_name)
        return response["DomainStatus"]["Endpoint"]

    def _aws_auth(self):
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

    def insert_bulk_payload(self, bulk_payload) -> tuple:
        success, errors = elasticsearch.helpers.bulk(self.es, bulk_payload)
        for e in errors:
            logger.error(f"ERROR: {json.dumps(e, indent=2, default=str)} \n")
        logger.info(f"SUCCESS: {success} ERROR: {len(errors)}")
        return success, errors

    @classmethod
    def list_indices(cls, domain_name):
        es = cls(domain_name)
        response = es.es.indices.get(index="cw-*", allow_no_indices=True)
        return frozenset(
            response[index]["settings"]["index"]["provided_name"] for index in response
        )

    @classmethod
    def delete_index(cls, domain_name, index):
        es = cls(domain_name)
        return es.es.indices.delete(index)


if __name__ == "__main__":
    import pprint
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "list":
        pprint.pprint(ElasticsearchWrapper.list_indices(sys.argv[2]))
    elif len(sys.argv) == 4 and sys.argv[1] == "delete":
        pprint.pprint(ElasticsearchWrapper.delete_index(sys.argv[2], sys.argv[3]))
    else:
        print(f"Usage: {sys.argv[0]} list|delete domain-name [pattern]")
        sys.exit(1)