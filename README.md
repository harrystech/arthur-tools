```plain-text
 _____     _   _              _____         _     
|  o  |___| |_| |_ _ _ ___   |_   _|___ ___| |___ 
|     |  _|  _|   | | |  _|    | | | o | o | |_ -|
|__|__|_| |_| |_|_|___|_|      |_| |___|___|_|___|
```

# Arthur Tools

We have some tools that we developed originally for [Project Arthur](https://github.com/harrystech/arthur-redshift-etl)
which then appeared to more generally useful. So here they are.

## Deploying CloudFormation templates

The script `do\_cloudformation.sh` will help with deploying CloudFormation templates and then updating or tearing down
the stacks.

Examples for Arthur ETL:
```bash
AWS_PROFILE=cloudformation-development \
  ../arthur-tools/bin/do_cloudformation.sh create dw-cluster dev \
  VpcStackName=... MasterUsername=... MasterUserPassword=... NodeType=... NumberOfNodes=... QueryConcurrency=...
```

## Deploying Lambdas

This will be a combination of uploading a deployment package and then updating the stack to move
the Lambda to the new version.  See examples in the `log_processing` directory.


## Centralized logging

Our ELK stack is really Elasticsearch + Lambda + Kibana where we use Lambdas to pull in logging information from
Lambdas, Services, and Applications.
