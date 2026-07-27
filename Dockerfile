FROM apache/airflow:3.0.3-python3.11

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

ENV PYTHONPATH="/opt/airflow/src:${PYTHONPATH}"
