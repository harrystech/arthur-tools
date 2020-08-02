# Misc commands

## Clear AWS values in your shell environment
    unset $(env | grep AWS | cut -d '=' -f1) 
    
## For serverless to pick up the AWS profile from env
    export AWS_SDK_LOAD_CONFIG=1
    export AWS_PROFILE=example_profile
