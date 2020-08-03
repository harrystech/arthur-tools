# Sending CloudWatch Logs to an Elasticsearch service

This service using the [Serverless](https://serverless.com/) framework will
index logs from [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) into an
Elasticsearch service.

Applications (most likely serverless microservices themselves) are expected to
emit their log lines in a JSON-compatible format.

## Indices and documents

We'll pick one index per month which is a trade-off between the number
of shards that we have available and the number documents (= log messages)
that we want to store.

Indices will follow this pattern: `cw-logs-{year}-{month}`.

**TODO** Add Lambda function that deletes indices after one year.

## Installation

### Docker

Install [Docker](https://docs.docker.com/install/).

### Local development

* Clone this repo
* `cd` into the working directory
* Use `bin/run_me.sh`

## Access management
As this application is deployed to and runs on AWS, developers on this project
need the following:
1. `aws-vault`
2. an AWS account with access to the required services

## Code & Config Separation
The `serverless.yml` file needs the following variables which are assumed to
be populated in the Docker container:

Name | Note
----|----
`ES_DOMAIN_NAME` | Name of the Elasticsearch domain, _e.g._ `dw-es-dev`

## Usage

Use `./bin/run_me.sh` to see your available options.

Examples:
```shell
bin/run_me.sh build
bin/run_me.sh python3 -m cw_logs_to_es.lambda_handler

aws-vault profile-with-enough-privileges
bin/run_me.sh sls-deploy
```

# Tips & Tricks

## Clear AWS values in your shell environment
    unset $(env | grep AWS | cut -d '=' -f1)
