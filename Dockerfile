FROM puckel/docker-airflow:1.10.2
LABEL maintainer="Colton Willig <coltonwillig@gmail.com>"

USER root

RUN apt-get update \
    && apt-get install -y \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /root
RUN pip3 install --upgrade pip==19.2.3
RUN pip3 install --no-cache-dir -r /root/requirements.txt

COPY src /usr/local/airflow
COPY config/airflow.cfg /usr/local/airflow/airflow.cfg

USER airflow

ENV PYTHONPATH "${PYTHONPATH}:/usr/local/airflow"
