# Interacting with the Elasticsearch cluster

## List indices
    curl -X GET https://${ES_HOST}:${ES_PORT}/_cat/indices

    curl -X GET https://${ES_HOST}:${ES_PORT}/_cat/indices/cw-\*

## Delete index
    curl -X DELETE https://${ES_HOST}:${ES_PORT}/cw-\*
