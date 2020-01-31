## Misc commands

#### clear aws values in env
    unset $(env | grep AWS | cut -d '=' -f1) 
    
#### for sls to pick up profile from env, need to run the following
    export AWS_SDK_LOAD_CONFIG=1 && \
    export AWS_PROFILE=example_profile

