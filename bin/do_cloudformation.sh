#! /bin/bash

set -e -u

if [[ $# -lt 3 || "$1" = "-h" ]]; then
    cat <<EOF

Usage:
  `basename $0` 'verb' 'object' 'env' [Key=Value [Key=Value ...]]

The following verbs are supported: create, update, and delete

We'll look for a description of the "object" in a template file.

The "env" parameter should describe the environment type, e.g. dev, prod, poc.

All other parameters will be passed to AWS CLI after transformation to "ParameterKey=Key,ParameterValue=Value" syntax.
Use 'UsePreviousValue' if you don't want to specify a new value.

EOF
    exit 0
fi

CF_VERB="$1"
CF_OBJECT="$2"
ENV_NAME="$3"
shift 3

CF_BASE_NAME="${CF_OBJECT//_/-}"
STACK_NAME="${CF_BASE_NAME}-${ENV_NAME}"

echo "Trying to \"$CF_VERB\" a \"$CF_OBJECT\" within stack \"$STACK_NAME\"..."

BINDIR=`dirname $0`
FOUND=no
TEMPLATE_DIRS=". ./cloudformation $BINDIR"
for TEMP_DIR in $TEMPLATE_DIRS; do
    TEMPLATE_FILE="$TEMP_DIR/$CF_OBJECT.yaml"
    if [[ -r "$TEMPLATE_FILE" ]]; then
        FOUND=yes
        break
    fi
done

if [[ "$FOUND" = "no" ]]; then
    echo "Cannot find template '$CF_OBJECT.yaml' in: $TEMPLATE_DIRS -- you lost it?"
    exit 1
fi

TEMPLATE_URI="file://$TEMPLATE_FILE"
echo "Using CloudFormation template in \"$TEMPLATE_URI\"..."

STACK_PARAMETERS=""
for KV in "$@"; do
    PARAMETER_KEY="${KV%%=*}"
    PARAMETER_VALUE="${KV#*=}"
    case "$PARAMETER_VALUE" in
        "UsePreviousValue")
          STACK_PARAMETERS="$STACK_PARAMETERS ParameterKey=$PARAMETER_KEY,UsePreviousValue=true"
          ;;
        *)
          STACK_PARAMETERS="$STACK_PARAMETERS ParameterKey=$PARAMETER_KEY,ParameterValue=$PARAMETER_VALUE"
          ;;
    esac
done

set -x
STACK_PARAMETERS="${STACK_PARAMETERS# }"

# Because of the "set -e", a failed validation will stop this script:
aws cloudformation validate-template --template-body "$TEMPLATE_URI" >/dev/null

case "$CF_VERB" in

  create)

    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body "$TEMPLATE_URI" \
        --on-failure DO_NOTHING \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters $STACK_PARAMETERS \
        --tags \
            "Key=user:project,Value=data-warehouse" \
            "Key=user:stack-env-name,Value=$ENV_NAME"
    ;;

  update)

    aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body "$TEMPLATE_URI" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters $STACK_PARAMETERS \
        --tags \
            "Key=user:project,Value=data-warehouse" \
            "Key=user:stack-env-name,Value=$ENV_NAME"
    ;;

  delete)

    aws cloudformation delete-stack \
        --stack-name "$STACK_NAME"
    ;;

  *)
    echo "Unexpected verb: $CF_VERB"
    exit 1
    ;;

esac

set +x
echo "To see resources for this stack, run:"
echo
echo "aws cloudformation list-stack-resources --stack-name \"$STACK_NAME\""
