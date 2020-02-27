FROM lambci/lambda:build-nodejs12.x

ENV SERVERLESS_VERSION=1.58.0

# initialize these as NONE because sls plugin install scream if they don't exist in env
ARG SLS_DEPLOYMENT_BUCKET="NONE"
ARG ES_HOST="NONE"
ARG ES_PORT="NONE"
ARG ES_CLUSTER_ARN="NONE"
ARG MONITORED_LOG_GROUP="NONE"

WORKDIR /app/

COPY serverless*.yml ./
RUN npm install -g serverless@$SERVERLESS_VERSION
RUN sls plugin install --name serverless-pseudo-parameters

COPY requirements.txt .
RUN pip3 install -r requirements.txt -t /app/python-requirements/

WORKDIR /app/de-cloudwatch-logs-to-elasticsearch/
