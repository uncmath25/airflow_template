from airflow import DAG
from airflow.contrib.operators.emr_add_steps_operator import EmrAddStepsOperator
from airflow.contrib.operators.emr_create_job_flow_operator import EmrCreateJobFlowOperator
from airflow.contrib.operators.emr_terminate_job_flow_operator import EmrTerminateJobFlowOperator
from airflow.contrib.sensors.emr_step_sensor import EmrStepSensor
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import json
import os
import uuid


default_args = {
    'owner': 'airflow',
    'email': ["coltonwillig@gmail.com"],
    'email_on_failure': True,
    'email_on_retry': False,
    'start_date': datetime(2019, 9, 21),
    'depends_on_past': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'max_active_runs': 1,
    'execution_timeout': timedelta(hours=4)
}

dag = DAG('emr',
          default_args=default_args,
          schedule_interval='@daily',
          catchup=False,
          concurrency=1)

AWS_CONN = 'aws_default'

SPARK_JOB_S3_URL = 's3://BUCKET/spark_job.py'

S3_PREFIX = 's3://'
HDFS_OUTPUT_PREFIX = 'hdfs://output/'
WRITE_PATHS_TO_DELETE = [
    'BUCKET/TABLE/application_run_uuid={application_run_uuid}'
]
WRITE_PATHS_TO_COPY_MAP = {
    'table': 'BUCKET/TABLE/application_run_uuid={application_run_uuid}'
}


def build_emr_pipeline_steps(application_run_uuid):
    return [
        {
            'Name': 'Spark App Job',
            'ActionOnFailure': 'CONTINUE',
            'HadoopJarStep': {
                'Jar': 'command-runner.jar',
                'Args': [
                    'spark-submit',
                    SPARK_JOB_S3_URL,
                    '--config',
                    json.dumps({
                        'application_run_uuid': application_run_uuid
                    })
                ]
            }
        }
    ]


def s3_write_deletes_runnable(**kwargs):
    paths_format_dict = {
        'application_run_uuid': str(kwargs['application_run_uuid'])
    }
    for s3_url in [S3_PREFIX + path.format(**paths_format_dict) for path in WRITE_PATHS_TO_DELETE]:
        print(f'Deleting S3 directory {s3_url}')
        os.system(f'aws rm {s3_url} --recursive')


def build_emr_s3_write_copy_steps(application_run_uuid):
    paths_format_dict = {
        'application_run_uuid': application_run_uuid
    }
    return {table: [
        {
            'Name': 'S3 Write Copy Job',
            'ActionOnFailure': 'CONTINUE',
            'HadoopJarStep': {
                'Jar': 'command-runner.jar',
                'Args': [
                    's3-dict-cp',
                    f'--src={HDFS_OUTPUT_PREFIX + WRITE_PATHS_TO_COPY_MAP[table].format(**paths_format_dict)}',
                    f'--dest={S3_PREFIX + WRITE_PATHS_TO_COPY_MAP[table].format(**paths_format_dict)}'
                ]
            }
        }
    ] for table in WRITE_PATHS_TO_COPY_MAP}


# Create EMR Cluster
EMR_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'emr.json')
with open(EMR_CONFIG_PATH, 'r') as f:
    EMR_CONFIG = json.load(f)


CREATE_EMR_CLUSTER_TASK_ID = 'create_emr_cluster'


def get_cluster_id():
    return "{{ ti.xcom_pull(task_ids='" + CREATE_EMR_CLUSTER_TASK_ID + "', key='return_value') }}"


create_cluster_task = EmrCreateJobFlowOperator(
    task_id=CREATE_EMR_CLUSTER_TASK_ID,
    job_flow_overrides=EMR_CONFIG,
    aws_conn_id=AWS_CONN,
    dag=dag
)


# Set UUID
SET_UUID_TASK_ID = 'set_uuid'


def get_uuid():
    return "{{ ti.xcom_pull(task_ids='" + SET_UUID_TASK_ID + "') }}"


set_uuid_task = PythonOperator(
    task_id=SET_UUID_TASK_ID,
    python_callable=lambda **kwargs: str(uuid.uuid4()),
    dag=dag
)

create_cluster_task >> set_uuid_task


# Run Application
STEP_ADDER_TASK_ID = 'pipeline_add_steps'

pipeline_step_adder_task = EmrAddStepsOperator(
    task_id=STEP_ADDER_TASK_ID,
    job_flow_id=get_cluster_id(),
    steps=build_emr_pipeline_steps(get_uuid()),
    aws_conn_id=AWS_CONN,
    dag=dag
)

pipeline_step_checker_task = EmrStepSensor(
    task_id='pipeline_watch_step',
    job_flow_id=get_cluster_id(),
    step_id="{{ ti.xcom_pull(task_ids='" + STEP_ADDER_TASK_ID + "', key='return_value')[0] }}",
    aws_conn_id=AWS_CONN,
    dag=dag
)

s3_write_deletes_task = PythonOperator(
    task_id='s3_write_deletes',
    python_callable=s3_write_deletes_runnable,
    provide_context=True,
    op_kwargs={},
    templates_dict={'exec_date': "{{ macro.ds_add(ds, -1) }}"},
    dag=dag
)

set_uuid_task >> pipeline_step_adder_task >> pipeline_step_checker_task >> s3_write_deletes_task

finished_write_copy_task = DummyOperator(task_id='finished_write_copy', dag=dag)

s3_write_copy_steps = build_emr_s3_write_copy_steps(get_uuid())
for table in WRITE_PATHS_TO_COPY_MAP:
    write_copy_step_adder_task_id = 's3_write_copy_add_steps_' + table
    s3_write_copy_step_adder_task = EmrAddStepsOperator(
        task_id=write_copy_step_adder_task_id,
        job_flow_id=get_cluster_id(),
        steps=s3_write_copy_steps[table],
        aws_conn_id=AWS_CONN,
        dag=dag
    )
    s3_write_copy_step_checker_task = EmrStepSensor(
        task_id='s3_write_copy_watch_step',
        job_flow_id=get_cluster_id(),
        step_id="{{ ti.xcom_pull(task_ids='" + write_copy_step_adder_task_id + "', key='return_value')[0] }}",
        aws_conn_id=AWS_CONN,
        dag=dag
    )
    s3_write_deletes_task >> s3_write_copy_step_adder_task >> s3_write_copy_step_checker_task >> finished_write_copy_task


# Terminate EMR Cluster
terminate_cluster_task = EmrTerminateJobFlowOperator(
    task_id='terminate_emr_cluster',
    job_flow_id=get_cluster_id(),
    aws_conn_id=AWS_CONN,
    dag=dag
)

finished_write_copy_task >> terminate_cluster_task
