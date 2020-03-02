# Airflow Template

### Description
This project provides an Airflow template for orchestrating an etl project with local Dockerized environment

### Local Usage
* Lint the repo: ` make flake `
* Test the files in *./tests/*: ` make test `
* The default ` make ` command runs both of the above commands
* Clean the repo of unnecessary caches: ` make clean `
* Start local Airflow webserver: ` make up `
* Stop local Airflow webserver: ` make down `
* Fill in *.env.template* with your aws credentials and save as *.env* in order to use aws services

### Deploy
` make deploy ` offer a template for deploying the Airflow docker image (along with dag files) to ECS
(Typically you would embed this deployment into a CD step, like say in an AWS **buildspec.yaml** file)

### Notes
This repo primary focuses on a local framework (and deployment stub) for developing Airflow DAGs.  Although the docker compose commands in this repo facilitate local Airflow development and testing, DAGs should still be tested in a "QA" environment (like say a separate "testing" AWS account) before deployment to a production setting.  Furthermore, any non-trivial business logic should be decoupled from the DAG: such python scripts should be maintained in a separate repo which maintains its own CI and CD pipeline with appropriate unit testing.  These scripts can also be developed into more sophisticated "apps" which can be maintained and deployed as their own python packages, particularly if they begin to exhibit sufficient complexity.
