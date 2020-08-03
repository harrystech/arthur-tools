FROM lambci/lambda:build-python3.8

RUN curl --silent --location https://rpm.nodesource.com/setup_12.x | bash - \
    && yum install --assumeyes nodejs \
    && yum clean all \
    && rm -rf /var/cache/yum

RUN npm install --global --unsafe-perm "serverless@1.77.1"

COPY serverless.yml requirements.txt /var/task/
RUN python3 -m pip install --requirement /var/task/requirements.txt --target /var/task \
    --no-cache-dir --disable-pip-version-check

WORKDIR /var/task
