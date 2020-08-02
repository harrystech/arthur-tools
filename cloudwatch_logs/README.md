# cloudwatch-logs

This service using the [Serverless](https://serverless.com/) framework will index logs
from [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) into an Elasticsearch service.

Applications (most likely serverless microservices themselves) are expected to emit their log lines
in a JSON-compatible format.

## Installation

### Docker

Install [Docker](https://docs.docker.com/install/).

### Local development

* Clone this repo
* `cd` into the working directory
* Build the Docker image
* Start a shell

## Access management
As this application is deployed to and runs on AWS, developers on this project need the following:
1. aws-vault
2. an AWS account with access to the required services
    
## Code & Config Separation
The serverless.yml file needs the following variables which are assumed to be populated in the Docker container
    
Name | Note
----|----
`SLS_DEPLOYMENT_BUCKET` | s3 bucket where the packaged applciation stack will be deployed
`ES_HOST` | host/endpoint
`ES_PORT` | port
`ES_CLUSTER_ARN`  | can be inferred from the cluster_name, but we find it straightforward to supply the full arn
`MONITORED_LOG_GROUP` | log group to be indexed - for now we only monitor 1

## Usage
    ./run.sh docker-build
    ./run.sh unit-tests
    ./run.sh sls-deploy-dev
    ./run.sh tail-logs
