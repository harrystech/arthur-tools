# Interacting with the Elasticsearch cluster

## List indices
    curl -X GET https://${ES_HOST}/_cat/indices

    curl -X GET https://${ES_HOST}/_cat/indices/cw-\*

## Delete index
    curl -X DELETE https://${ES_HOST}/cw-testloggroup-2020-08-03
