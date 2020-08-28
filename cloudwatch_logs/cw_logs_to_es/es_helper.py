import json
import logging
import os
from typing import Any, FrozenSet, Iterable

import boto3
import elasticsearch
import elasticsearch.helpers
import requests_aws4auth

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

region_name = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
session = boto3.Session(region_name=region_name)


class ElasticsearchWrapper:
    def __init__(self, domain_name: str) -> None:
        host = ElasticsearchWrapper.find_es_host(domain_name)
        self.elasticsearch = elasticsearch.Elasticsearch(
            hosts=[{"host": host, "port": 443}],
            use_ssl=True,
            verify_certs=True,
            connection_class=elasticsearch.RequestsHttpConnection,
            http_auth=self._aws_auth(),
            http_compress=True,
            send_get_body_as="POST",
        )
        logger.info(f"Cluster info: {self.elasticsearch.info()}")

    @staticmethod
    def find_es_host(domain_name: str) -> str:
        client = session.client("es")
        response = client.describe_elasticsearch_domain(DomainName=domain_name)
        return str(response["DomainStatus"]["Endpoint"])

    @staticmethod
    def _aws_auth() -> Any:
        credentials = session.get_credentials()
        aws4auth = requests_aws4auth.AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            session.region_name,
            "es",
            session_token=credentials.token,
        )

        def wrapped_aws4auth(request: Any) -> Any:
            return aws4auth(request)

        return wrapped_aws4auth

    def insert_bulk_payload(self, bulk_payload: Iterable[dict]) -> tuple:
        success, errors = elasticsearch.helpers.bulk(self.elasticsearch, bulk_payload)
        for i, e in enumerate(errors):
            logger.error(f"ES bulk error #{i+1}:\n{json.dumps(e, indent=2, default=str)}\n")
        logger.info(
            "Bulk upload finished.", extra={"success_count": success, "error_count": len(errors)}
        )
        return success, errors

    @classmethod
    def list_indices(cls, domain_name: str) -> FrozenSet[str]:
        es = cls(domain_name)
        response = es.elasticsearch.indices.get(index="cw-*", allow_no_indices=True)
        return frozenset(
            response[index]["settings"]["index"]["provided_name"] for index in response
        )

    @classmethod
    def delete_index(cls, domain_name: str, index: str) -> dict:
        es = cls(domain_name)
        return dict(es.elasticsearch.indices.delete(index, ignore_unavailable=True))


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "list":
        print("\n".join(ElasticsearchWrapper.list_indices(sys.argv[2])))
    elif len(sys.argv) == 4 and sys.argv[1] == "delete":
        resp = ElasticsearchWrapper.delete_index(sys.argv[2], sys.argv[3])
        print(json.dumps(resp, indent=4, sort_keys=True))
    else:
        print(f"Usage: {sys.argv[0]} list|delete domain-name [pattern]")
        sys.exit(1)
