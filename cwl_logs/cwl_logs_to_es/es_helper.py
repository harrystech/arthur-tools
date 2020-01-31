import gzip
import io
import json
import logging
import os

import boto3

import elasticsearch
import elasticsearch.helpers
from elasticsearch import Elasticsearch, connection as es_connection
import requests_aws4auth



class ElasticSearchWrapper:
    log = logging.getLogger(__name__)
    es: Elasticsearch = None

    def __init__(self, es_host, es_port):
        self.session = boto3.Session(
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
            region_name=os.environ.get('AWS_REGION')
        )
        self.aws_es_client = self.session.client('es')
        self.es = self.get_connected_es_instance(host=es_host, port=es_port)
        self.log.info("Finish init")


    def get_connected_es_instance(self, host, port) -> Elasticsearch:
        es = Elasticsearch(
            hosts=[{"host": host, "port": port}],
            use_ssl=True,
            verify_certs=True,
            connection_class=es_connection.RequestsHttpConnection,
            http_auth=self._aws_auth(),
            send_get_body_as="POST"
        )
        self.log.info(es.info)
        return es

    def _aws_auth(self):
        credentials = self.session.get_credentials()
        aws4auth = requests_aws4auth.AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.session.region_name,
            "es",
            session_token=credentials.token)

        def wrapped_aws4auth(request):
            return aws4auth(request)

        return wrapped_aws4auth

    def insert_bulk_payload(self, bulk_payload) -> tuple:
        success, errors = elasticsearch.helpers.bulk(self.es, bulk_payload)
        for e in errors:
            self.log.error(f"ERROR: {json.dumps(e, indent=2, default=str)} \n")
        self.log.info(f"SUCCESS: {success} ERROR: {len(errors)}")
        return success, errors




