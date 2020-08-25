#!/usr/bin/env bash

set -o errexit -o nounset

PROJ_NAME="cw_logs_to_es"

if [[ $# -gt 0 ]]; then
    cmd="$1"
    shift 1
else
    cmd="help"
fi

carp () {
    echo "$*" 2>&1
    exit 1
}

display_help () {
    cat <<USAGE
Usage: $0 command [options]

Available commands to work with Docker image or container:
* build - build a Docker image
* shell - run a shell inside the Docker container
* python3 - run a python interpreter (use "-m $PROJ_NAME.lambda_handler")

Available commands to use Serverless for deployment:
* sls-deploy - use serverless to deploy the function
* sls-logs - gather the logs

Available commands to work with Elasticsearch domains:
* delete-index - delete a specific index
* describe-elasticsearch-domain - use aws-cli to describe the domain (give name as option!)
* list-indices - list indices in the ES cluster

*Available commands to work with Log Groups:
* add-subscription - add subscription to log group to be ingested by "$PROJ_NAME"
* describe-subscription - use aws-cli to describe the subscriptions (give log group as option)
* list-log-groups - list log groups available in CloudWatch Logs

NOTE
The file "serverless.yml" is part of the image. Th image is only automatically re-built for deploys.

USAGE
}

docker_aws () {
    docker_run /var/lang/bin/aws "$@"
}

docker_aws_put_subscription_filter () {
    # TODO(tom): move this into Python to leverage serverless setup
    AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
    FUNCTION_NAME="CloudWatchLogsToElasticsearch-dev-lambdaHandler"
    LOG_GROUP_NAME="$1"

    DESTINATION_ARN="arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT:function:$FUNCTION_NAME"
    SOURCE_ARN="arn:aws:logs:$AWS_REGION:$AWS_ACCOUNT:log-group:$LOG_GROUP_NAME:*"

    docker_aws lambda add-permission \
        --function-name "$DESTINATION_ARN" \
        --action "lambda:InvokeFunction" \
        --principal "logs.$AWS_REGION.amazonaws.com" \
        --source-arn "$SOURCE_ARN" \
        --source-account "$AWS_ACCOUNT" \
        --statement-id "$(uuidgen)"

    docker_aws logs put-subscription-filter \
        --log-group-name $LOG_GROUP_NAME \
        --filter-name "Lambda_$FUNCTION_NAME" \
        --filter-pattern "" \
        --destination-arn "$DESTINATION_ARN"

    docker_aws logs describe-subscription-filters --log-group-name "$LOG_GROUP_NAME"
}

docker_build () {
    set -o xtrace
    docker build --tag "$PROJ_NAME" .
}

docker_run () {
    set -o xtrace
    docker run --rm --interactive --tty --volume "$PWD/$PROJ_NAME":"/var/task/$PROJ_NAME" \
        --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --env AWS_SESSION_TOKEN \
        --env AWS_REGION --env AWS_DEFAULT_REGION --env ES_DOMAIN_NAME \
        "$PROJ_NAME":latest "$@"
}

docker_sls () {
    docker_run /usr/bin/sls "$@"
}

case $cmd in
    '-h' | 'help')
        display_help
        ;;
    'add-subscription')
        LOG_GROUP_NAME="${1?You need to specify a log group name as arg}"
        docker_aws_put_subscription_filter $LOG_GROUP_NAME
        ;;
    'build')
        docker_build
        ;;
    'delete-index')
        [[ "${ES_DOMAIN_NAME-notset}" = "notset" ]] && carp "ES_DOMAIN_NAME is not set"
        INDEX_NAME="${1?You need to specify a index as arg}"
        docker_run /var/lang/bin/python3 -m cw_logs_to_es.es_helper delete "$ES_DOMAIN_NAME" "$INDEX_NAME"
        ;;
    'describe-elasticsearch-domain')
        # If you're running a domain called "notset", then you're SOL.
        [[ "${ES_DOMAIN_NAME-notset}" = "notset" ]] && carp "ES_DOMAIN_NAME is not set"
        docker_aws es describe-elasticsearch-domain --domain-name "$ES_DOMAIN_NAME"
        ;;
    'describe-subscription')
        LOG_GROUP_NAME="${1?You need to specify a log group name as arg}"
        docker_aws logs describe-subscription-filters --log-group-name "$LOG_GROUP_NAME"
        ;;
    'list-indices')
        [[ "${ES_DOMAIN_NAME-notset}" = "notset" ]] && carp "ES_DOMAIN_NAME is not set"
        docker_run /var/lang/bin/python3 -m cw_logs_to_es.es_helper list "$ES_DOMAIN_NAME"
        ;;
    'list-log-groups')
        docker_aws logs describe-log-groups --query 'logGroups[*].logGroupName'
        ;;
    'python3')
        docker_run /var/lang/bin/python3 "$@"
        ;;
    'shell')
        docker_run /usr/bin/bash "$@"
        ;;
    'sls-deploy')
        [[ "${ES_DOMAIN_NAME-notset}" = "notset" ]] && carp "ES_DOMAIN_NAME is not set"
        docker_build
        docker_sls deploy --verbose --force "$@"
        ;;
    'sls-logs')
        [[ "${ES_DOMAIN_NAME-notset}" = "notset" ]] && carp "ES_DOMAIN_NAME is not set"
        # export AWS_SDK_LOAD_CONFIG=1
        docker_sls logs --function lambdaHandler "$@"
        ;;
    *)
        echo "Unknown command: $cmd"
        display_help
        exit 1
        ;;
esac
