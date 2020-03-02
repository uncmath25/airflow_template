.PHONY: all clean build flake down test up

SHELL := /bin/bash

NAME := uncmath25/airflow-template

all: flake test

clean:
	@echo "*** Cleaning the repo ***"
	rm -rf `find . -name __pycache__`
	rm -rf .pytest_cache

build: clean
	@echo "*** Building Airflow image ***"
	docker build -t $(NAME) .

flake: build
	@echo "*** Linting python code ***"
	flake8 --ignore="E501,W503" src

test: build
	@echo "*** Running unit testing via pytest ***"
	docker-compose -f docker-compose.yml run --rm -v "tests:/usr/local/airflow/tests" worker bash -c "pytest tests"
	make down

down:
	@echo "*** Stopping airflow docker containers ***"
	docker-compose -f docker-compose.yml down -v --remove-orphans

up: build down
	@echo "*** Running airflow server ***"
	@echo "*** Remember to correctly configure the .env file ***"
	docker-compose -f docker-compose.yml up --remove-orphans -d
	@echo "*** View server at http://localhost:8080 ***"

deploy: all
	@echo "*** Deploying Airflow Docker image to ECS ***"
	$$(aws ecr get-login --no-include-email --region $AWS_REGION)
	docker build -t uncmath25/airflow .
	docker tag uncmath25/airflow $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
	docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
	aws ecs update-service --cluster $AIRFLOW_CLUSTER_NAME --service $AIRFLOW_WEBSERVER_SERVICE_NAME --force-new-deployment
	aws ecs update-service --cluster $AIRFLOW_CLUSTER_NAME --service $AIRFLOW_FLOWER_SERVICE_NAME --force-new-deployment
	aws ecs update-service --cluster $AIRFLOW_CLUSTER_NAME --service $AIRFLOW_SCHEDULER_SERVICE_NAME --force-new-deployment
	aws ecs update-service --cluster $AIRFLOW_CLUSTER_NAME --service $AIRFLOW_WORKER_SERVICE_NAME --force-new-deployment
