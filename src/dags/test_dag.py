from airflow import DAG
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
    'start_date': datetime(2025, 1, 12),
    'depends_on_past': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'max_active_runs': 1,
    'execution_timeout': timedelta(hours=4)
}

dag = DAG('test',
          default_args=default_args,
          schedule_interval='@daily',
          catchup=False,
          concurrency=1)

# Set UUID
SET_UUID_TASK_ID = 'set_uuid'

def sample_runnable(**kwargs):
    print(f'uuid: {kwargs["ti"].xcom_pull(task_ids=SET_UUID_TASK_ID)}')
    print(kwargs)

create_uuid_task = PythonOperator(
    task_id=SET_UUID_TASK_ID,
    python_callable=lambda **kwargs: str(uuid.uuid4()),
    dag=dag
)

dummy_task = DummyOperator(task_id='dummy', dag=dag)

sample_task = PythonOperator(
    task_id='sample',
    python_callable=sample_runnable,
    provide_context=True,
    templates_dict={'exec_date': "{{ macros.ds_add(ds, -1) }}"},
    dag=dag
)

create_uuid_task >> dummy_task >> sample_task
