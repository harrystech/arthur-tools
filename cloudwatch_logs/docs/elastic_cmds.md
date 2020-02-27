##### list indices
    curl GET https://${ES_HOST}:${ES_PORT}/_cat/indices
    
    curl GET https://${ES_HOST}:${ES_PORT}/_cat/indices/cwl-\*
    
##### delete index
    curl -X DELETE https://${ES_HOST}:${ES_PORT}/cwl-\*
