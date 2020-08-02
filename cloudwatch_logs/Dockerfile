FROM lambci/lambda:build-python3.8

RUN curl --silent --location https://rpm.nodesource.com/setup_12.x | bash - \
    && yum install --assumeyes nodejs \
    && yum clean all

RUN npm install --global --unsafe-perm "serverless"

# initialize these as NONE because sls plugin install scream if they don't exist in env
ARG SLS_DEPLOYMENT_BUCKET="NONE"
ARG ES_HOST="NONE"
ARG ES_PORT="NONE"
ARG ES_CLUSTER_ARN="NONE"
ARG MONITORED_LOG_GROUP="NONE"

WORKDIR /app/

COPY serverless*.yml ./

COPY requirements.txt .
RUN pip3 install -r requirements.txt -t /app/python-requirements/

WORKDIR /app/de-cloudwatch-logs-to-elasticsearch/
