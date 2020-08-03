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

Available commands:
* build - build a Docker image
* shell - run a shell inside the Docker container
* python3 - run a python interpreter (use "-m $PROJ_NAME.lambda_handler")
* describe-elasticsearch-domain - use aws-cli to describe the domain (give name as option!)
* indices - list indices in the ES cluster
* sls-deploy - use serverless to deploy the function
* sls-logs - gather the logs
* add-subscription - add subscription to log group to be ingested by "$PROJ_NAME"

The file "serverless.yml" is part of th image. So you may have to call build more often.

USAGE
}

docker_build () {
    set -x
    docker build --tag "$PROJ_NAME" .
}

docker_run () {
    set -x
    docker run --rm --interactive --tty --volume "$PWD/$PROJ_NAME":"/var/task/$PROJ_NAME" \
        --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --env AWS_SESSION_TOKEN \
        --env AWS_REGION --env ES_DOMAIN_NAME \
        "$PROJ_NAME":latest "$@"
}

case $cmd in
    '-h' | 'help')
        display_help
        ;;
    'build')
        docker_build "$@"
        ;;
    'shell')
        docker_run /usr/bin/bash "$@"
        ;;
    'python3')
        docker_run /var/lang/bin/python3 "$@"
        ;;
    'describe-elasticsearch-domain')
        docker_run /var/lang/bin/aws es describe-elasticsearch-domain --domain-name "$ES_DOMAIN_NAME"
        ;;
    'indices')
        ES_ENDPOINT="${1?Missing endpoint from first args}"
        set -x
        curl "${ES_ENDPOINT}/_cat/indices"
        ;;
    'sls-deploy')
        # If you're running a domain called "notset", then you're SOL.
        [[ "${ES_DOMAIN_NAME-notset}" = "notset" ]] && carp "ES_DOMAIN_NAME is not set"
        docker_run /usr/bin/sls deploy --verbose --force "$@"
        ;;
    'sls-logs')
        [[ "${ES_DOMAIN_NAME-notset}" = "notset" ]] && carp "ES_DOMAIN_NAME is not set"
        export AWS_SDK_LOAD_CONFIG=1
        docker_run /usr/bin/sls logs --function lambdaHandler "$@"
        ;;
    'add-subscription')
        carp "Left to the reader as an exercise"
        exit 1
        ;;
    *)
        echo "Unknown command: $cmd"
        display_help
        exit 1
        ;;
esac
