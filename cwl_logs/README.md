# cloudwatch-logs-to-elasticsearch
Codebase for the indexing of structured cloudwatch logs into elasticsearch.

This is a serverless microservice built on the serverless framework.

## Runtime and platform dependencies
    Docker
    Docker image: lambci/lambda:build-nodejs12.x
    Python3.8
    Nodejs12.x
    Serverless@1.5.8


## Access management
As this application is deployed to and runs on AWS, developers on this project need the following:

    1) aws-vault
    2) an aws account with access to the required services [TODO: enumerate these]
    
## Code organization
    Lambda handler:           lambda_handler.py
    cloudwatch log parser:    ClodWatchLogsParser
    elasticsearch helper:     ElasticSearchWrapper
    
    1) At startup the lambda instantiates a ClodWatchLogsParser and a ElasticSearchWrapper
    2) The lambda receives a cloudwatch log event. 
    3) the lambda uses the ClodWatchLogsParser to parse the cloudwatch logs into an elasticsearch document. 
    4) The lambda uses the ElasticSearchWrapper to insert the document into elasticsearch
    
## Code & Config Separation
    The serverless.yml file needs the following variables which are assumed to be populated in the docker container
    
    SLS_DEPLOYMENT_BUCK      [s3 bucket where the packaged applciation stack will be deployed]
    ES_HOST                  [host/endpoint]
    ES_PORT                  [port]
    ES_CLUSTER_ARN           [can be inferred from the cluster_name, but we find it starightforward to supply the full arn]
    MONITORED_LOG_GROUP      [log group to be indexed - for now we only monitor 1]


## To run some commands and see output
Check out the acceptance criteria docs: **docs/acceptance_criteria.md**
    
      
## Local development and deployment
    1)  git clone [THIS REPO] and cd [THIS REPO] 
    2)  ./run docker-build             [builds docker dev env]
    3)  ./run unit-tests               [run unit test cases]
    4)  ./run sls-deploy-dev           [deploys stack to dev]
    5)  ./run logs                     [tail the lambda logs in dev]
    6)  invoke the monitored lambda and you should see this lambda's logs as it indexes the cwl logs
    


    


 

 
