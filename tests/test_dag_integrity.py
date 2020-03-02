# from airflow import settings
from airflow.models import Connection, DAG, DagBag
import importlib
import os
import pytest


DAG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dags')
DAG_FILES = [f for f in os.listdir(DAG_PATH) if f.endswith('.py')]

# CONNECTIONS_IDS = []
# session = settings.Session()
# for conn_id in CONNECTIONS_IDS:
#     session.add(Connection(conn_id=conn_id))
# session.commit()


@pytest.fixture(scope='module')
def dag_bag():
    return DagBag(include_examples=False)


def test_dag_integrity(dag_bag):
    assert len(dag_bag.import_errors) == 0, dag_bag.import_errors


@pytest.mark.parametrize('dag_file', DAG_FILES)
def test_import_dag_files(dag_file):
    module_name, _ = os.path.splitext(dag_file)
    module_path = os.path.join(DAG_PATH, dag_file)
    mod_spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(module)
    assert any(isinstance(v, DAG) for v in vars(module).values())
