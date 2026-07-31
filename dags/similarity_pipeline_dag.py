import os

from datetime import datetime

import requests
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


def notify_teams_on_failure(context):
    webhook_url = os.environ.get("MSTEAMS_WEBHOOK_URL")

    if webhook_url is None:
        return

    task_instance = context["task_instance"]
    task_id = task_instance.task_id
    dag_id = task_instance.dag_id
    try_number = task_instance.try_number
    execution_date = context.get("logical_date", context.get("ds"))
    log_url = task_instance.log_url

    message = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": (
                        "http://adaptivecards.io/schemas/"
                        "adaptive-card.json"
                    ),
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Airflow task failed",
                            "weight": "Bolder",
                            "size": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": f"DAG: {dag_id}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Task: {task_id}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Try number: {try_number}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Run date: {execution_date}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Logs: {log_url}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": (
                                "Contact: siranush.hakobyan@quantori.academy"
                            ),
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": (
                                "PS: don't buy a laptop with 8GB RAM 🥲"
                            ),
                            "wrap": True,
                            "isSubtle": True,
                        },
                        {
                            "type": "Image",
                            "url": (
                                "https://media1.tenor.com/m/"
                                "9PR5loGMyLQAAAAC/shocked-wow.gif"
                            ),
                            "size": "Medium",
                        },
                    ],
                },
            }
        ],
    }
    requests.post(webhook_url, json=message)


def run_sql_file(sql_path):
    import os
    import psycopg2

    connection = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    cursor = connection.cursor()

    with open(sql_path) as f:
        cursor.execute(f.read())

    connection.commit()
    cursor.close()
    connection.close()


default_args = {
    "owner": "siran",
    "retries": 1,
    "on_failure_callback": notify_teams_on_failure,
}

with DAG(
    dag_id="chembl_similarity_pipeline",
    default_args=default_args,
    description=(
        "ChEMBL molecule similarity pipeline: "
        "ingest -> load -> similarity -> mart -> S3"
    ),
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["chembl", "similarity"],
) as dag:

    run_ingestion = BashOperator(
        task_id="run_ingestion",
        bash_command="python -u /opt/airflow/src/run_full_ingestion.py",
    )

    load_to_bronze = BashOperator(
        task_id="load_to_bronze",
        bash_command="python -u /opt/airflow/src/load_to_bronze.py",
    )

    populate_dim_molecule = PythonOperator(
        task_id="populate_dim_molecule",
        python_callable=run_sql_file,
        op_kwargs={"sql_path": "/opt/airflow/sql/populate_dim_molecule.sql"},
    )

    compute_similarity = BashOperator(
        task_id="compute_similarity",
        bash_command="python -u /opt/airflow/src/compute_similarity.py",
    )

    # upload_fingerprints_to_s3 and compute_full_similarity_to_s3 each
    # independently fingerprint all ~2.9M molecules into memory. Running
    # both at once caused an OOM kill on the 8GB Mac, so they share a
    # 1-slot pool to force them to run one at a time instead of relying
    # on manual timing.
    upload_fingerprints_to_s3 = BashOperator(
        task_id="upload_fingerprints_to_s3",
        bash_command="python -u /opt/airflow/src/"
                     "upload_fingerprints_to_s3.py",
        pool="memory_heavy",
    )

    compute_full_similarity_to_s3 = BashOperator(
        task_id="compute_full_similarity_to_s3",
        bash_command="python -u /opt/airflow/src/"
                     "compute_full_similarity_to_s3.py",
        pool="memory_heavy",
    )

    create_views = PythonOperator(
        task_id="create_views",
        python_callable=lambda: [
            run_sql_file(f"/opt/airflow/sql/{filename}")
            for filename in [
                "avg_similarity_per_source.sql",
                "avg_alogp_deviation_per_source.sql",
                "similarity_pivot.sql",
                "similarity_chain.sql",
                "avg_similarity_grouped.sql",
            ]
        ],
    )

    run_ingestion >> load_to_bronze >> populate_dim_molecule
    populate_dim_molecule >> compute_similarity
    compute_similarity >> upload_fingerprints_to_s3
    compute_similarity >> compute_full_similarity_to_s3
    compute_similarity >> create_views
