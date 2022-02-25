AWS_PROFILE=everystreet-prod
REPO_NAME=everystreet-app
REPO_URI_PREFIX=319140110208.dkr.ecr.us-east-1.amazonaws.com
REPO_URI=${REPO_URI_PREFIX}/${REPO_NAME}

# The image must be built for the target ECS instance platform, which is linux/amd64 for now.
docker build --platform linux/amd64 -t ${REPO_NAME} .
docker tag ${REPO_NAME}:latest ${REPO_URI}:latest
aws ecr get-login-password --profile "$AWS_PROFILE" | docker login --username AWS --password-stdin ${REPO_URI_PREFIX}
docker push ${REPO_URI}:latest
NEW_DEFINITION=$(aws ecs register-task-definition --cli-input-json file://task-definition.json --profile "$AWS_PROFILE")

# To update the service, run the following lines.
NEW_VERSION=$(echo $NEW_DEFINITION | jq '.taskDefinition.revision')
aws ecs update-service --service ${REPO_NAME} --task-definition ${REPO_NAME}:${NEW_VERSION} --profile "$AWS_PROFILE"
