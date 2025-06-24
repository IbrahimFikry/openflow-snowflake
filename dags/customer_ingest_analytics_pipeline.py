from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta, datetime
import logging
from airflow.hooks.base import BaseHook
from pymongo import MongoClient
import pandas as pd
import os
from urllib.parse import quote_plus
import boto3
from botocore.client import Config
from sqlalchemy import create_engine
import subprocess

# Define default arguments
default_args = {
    'owner': 'Ibrahim Fikry',
    'depends_on_past': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
with DAG(
    dag_id='customer_ingest_analytics_pipeline',
    default_args=default_args,
    description='Extract customer data -> MinIO -> PostgreSQL -> dbt transform',
    schedule_interval='@daily',
    start_date=days_ago(1),
    catchup=False,
    tags=['customer', 'analytics', 'minio', 'dbt'],
) as dag:

    def extract_customer_data(**kwargs): 
        logging.info("Connecting to MongoDB...")
        conn = BaseHook.get_connection('mongo_vired') 

        extra = conn.extra_dejson
        logging.info(extra.get('uri'))
        uri = extra.get('uri') 

        client = MongoClient(uri)
        db = client[conn.schema]  # e.g., 'vired'
        collection = db['customer']

        logging.info("Querying customer collection...")
        data = list(collection.find())

        if not data:
            logging.warning("No customer data found.")
            return

        logging.info("Converting data to DataFrame...")
        df = pd.DataFrame(data)

        # Drop MongoDB's _id field if present
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'customer_data_{timestamp}.csv'
        output_path = f'/tmp/{filename}'
        df.to_csv(output_path, index=False)

        logging.info(f"Saved extracted customer data to {output_path}")

        # Optional: Push XCom so next task can use the file path
        kwargs['ti'].xcom_push(key='customer_csv_path', value=output_path)
    def save_to_minio(**kwargs):
        logging.info("Preparing to save file to MinIO...")

        # Pull the file path from XCom
        ti = kwargs['ti']
        file_path = ti.xcom_pull(key='customer_csv_path', task_ids='extract_customer_data')

        if not file_path or not os.path.exists(file_path):
            logging.error(f"File {file_path} not found.")
            return

        filename = os.path.basename(file_path)
        bucket_name = 'vired'

        # Get MinIO connection info from Airflow
        conn = BaseHook.get_connection('minio_conn')
        extra = conn.extra_dejson

        endpoint_url = extra.get('host')
        aws_access_key_id = extra.get('aws_access_key_id')
        aws_secret_access_key = extra.get('aws_secret_access_key')

        logging.info(f"Connecting to MinIO at {endpoint_url}...")

        s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )

        try:
            s3.head_bucket(Bucket=bucket_name)
        except Exception as e:
            logging.warning(f"Bucket '{bucket_name}' not found. Creating it...")
            s3.create_bucket(Bucket=bucket_name)

        logging.info(f"Uploading {filename} to bucket '{bucket_name}'...")
        with open(file_path, 'rb') as f:
            s3.upload_fileobj(f, bucket_name, filename)

        logging.info(f"File uploaded to MinIO successfully as {filename} in bucket {bucket_name}")

        # Optional: push the object name to XCom for the next task
        ti.xcom_push(key='minio_object_key', value=filename)
    def load_to_postgres(**kwargs):
        logging.info("Starting load from MinIO to PostgreSQL...")

        # Get CSV filename from XCom
        ti = kwargs['ti']
        filename = ti.xcom_pull(key='minio_object_key', task_ids='save_to_minio')
        if not filename:
            logging.error("No file name found in XCom.")
            return

        # MinIO connection
        conn_minio = BaseHook.get_connection('minio_conn')
        extra_minio = conn_minio.extra_dejson
        endpoint_url = extra_minio.get('host')
        aws_access_key_id = extra_minio.get('aws_access_key_id')
        aws_secret_access_key = extra_minio.get('aws_secret_access_key')

        s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )

        bucket_name = 'vired'
        download_path = f'/tmp/{filename}'

        # Download CSV file
        logging.info(f"Downloading {filename} from MinIO bucket '{bucket_name}'...")
        with open(download_path, 'wb') as f:
            s3.download_fileobj(bucket_name, filename, f)
        logging.info(f"Downloaded to {download_path}")

        # Load CSV into DataFrame
        df = pd.read_csv(download_path)

        # PostgreSQL connection
        conn_pg = BaseHook.get_connection('postgres_analytics')
        user = conn_pg.login
        password = conn_pg.password
        host = conn_pg.host
        port = conn_pg.port
        schema = conn_pg.schema or 'public'

        db_url = f"postgresql://{user}:{password}@{host}:{port}/{schema}"
        engine = create_engine(db_url)

        table_name = "stg_customer_raw"

        # Load DataFrame into PostgreSQL
        logging.info(f"Loading data into PostgreSQL table '{table_name}'...")
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        logging.info("Data successfully loaded into PostgreSQL.")
    def run_dbt_transform(**kwargs):
        logging.info("Starting dbt transformation...")

        # Path to your dbt project inside the Airflow container
        dbt_project_path = "/opt/airflow/dbt_project"

        # Optional: set environment variables if needed
        env = os.environ.copy()

        try:
            logging.info("Running dbt run for fct_customer_by_country...")
            result = subprocess.run(
                ["dbt", "run", "--select", "fct_customer_by_country"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(result.stdout)
            if result.returncode != 0:
                logging.error(result.stderr)
                raise Exception("dbt run failed")

            logging.info("Running dbt test...")
            test_result = subprocess.run(
                ["dbt", "test", "--select", "fct_customer_by_country"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(test_result.stdout)
            if test_result.returncode != 0:
                logging.error(test_result.stderr)
                raise Exception("dbt test failed")

            logging.info("dbt transformation completed successfully.")
        except Exception as e:
            logging.error(f"dbt transform failed: {str(e)}")
            raise
    def run_dbt_transform_monthly(**kwargs):
        logging.info("Starting dbt transformation...")

        # Path to your dbt project inside the Airflow container
        dbt_project_path = "/opt/airflow/dbt_project"

        # Optional: set environment variables if needed
        env = os.environ.copy()

        try:
            logging.info("Running dbt run for fct_customer_by_month...")
            result = subprocess.run(
                ["dbt", "run", "--select", "fct_customer_by_month"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(result.stdout)
            if result.returncode != 0:
                logging.error(result.stderr)
                raise Exception("dbt run failed")

            logging.info("Running dbt test...")
            test_result = subprocess.run(
                ["dbt", "test", "--select","fct_customer_by_month"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(test_result.stdout)
            if test_result.returncode != 0:
                logging.error(test_result.stderr)
                raise Exception("dbt test failed")

            logging.info("dbt transformation completed successfully.")
        except Exception as e:
            logging.error(f"dbt transform failed: {str(e)}")
            raise
    def run_dbt_transform_platform(**kwargs):
        logging.info("Starting dbt transformation...")

        # Path to your dbt project inside the Airflow container
        dbt_project_path = "/opt/airflow/dbt_project"

        # Optional: set environment variables if needed
        env = os.environ.copy()

        try:
            logging.info("Running dbt run for fct_customer_by_platform...")
            result = subprocess.run(
                ["dbt", "run", "--select", "fct_customer_by_platform"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(result.stdout)
            if result.returncode != 0:
                logging.error(result.stderr)
                raise Exception("dbt run failed")

            logging.info("Running dbt test...")
            test_result = subprocess.run(
                ["dbt", "test", "--select","fct_customer_by_platform"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(test_result.stdout)
            if test_result.returncode != 0:
                logging.error(test_result.stderr)
                raise Exception("dbt test failed")

            logging.info("dbt transformation completed successfully.")
        except Exception as e:
            logging.error(f"dbt transform failed: {str(e)}")
            raise
    def run_dbt_transform_watchlist(**kwargs):
        logging.info("Starting dbt transformation...")

        # Path to your dbt project inside the Airflow container
        dbt_project_path = "/opt/airflow/dbt_project"

        # Optional: set environment variables if needed
        env = os.environ.copy()

        try:
            logging.info("Running dbt run for fct_customer_by_watchlist...")
            result = subprocess.run(
                ["dbt", "run", "--select", "fct_customer_by_watchlist"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(result.stdout)
            if result.returncode != 0:
                logging.error(result.stderr)
                raise Exception("dbt run failed")

            logging.info("Running dbt test...")
            test_result = subprocess.run(
                ["dbt", "test", "--select", "fct_customer_by_watchlist"],
                cwd=dbt_project_path,
                env=env,
                capture_output=True,
                text=True
            )
            logging.info(test_result.stdout)
            if test_result.returncode != 0:
                logging.error(test_result.stderr)
                raise Exception("dbt test failed")

            logging.info("dbt transformation completed successfully.")
        except Exception as e:
            logging.error(f"dbt transform failed: {str(e)}")
            raise

    t4_dbt_bash_command = """
    set -e
    echo "Starting dbt transformation..."

    cd /opt/airflow

    echo "Running dbt run for fct_customer_by_country..."
    echo "meow"
    dbt run --select fct_customer_by_country

    echo "Running dbt test for fct_customer_by_country..."
    dbt test --select fct_customer_by_country

    echo "dbt transformation completed successfully."
    """

    t5_dbt_bash_command = """
    set -e
    echo "Starting dbt transformation..."

    cd /opt/airflow

    echo "Running dbt run for fct_customer_by_monthly..."
    echo "meow"
    dbt run --select fct_customer_by_month

    echo "Running dbt test for fct_customer_by_monthly..."
    dbt test --select fct_customer_by_month

    echo "dbt transformation completed successfully."
    """

    t6_dbt_bash_command = """
    set -e
    echo "Starting dbt transformation..."

    cd /opt/airflow

    echo "Running dbt run for fct_customer_by_platform..."
    echo "meow"
    dbt run --select fct_customer_by_platform

    echo "Running dbt test for fct_customer_by_platform..."
    dbt test --select fct_customer_by_platform

    echo "dbt transformation completed successfully."
    """

    t7_dbt_bash_command = """
    set -e
    echo "Starting dbt transformation..."

    cd /opt/airflow

    echo "Running dbt run for fct_customer_by_watchlist..."
    echo "meow"
    dbt run --select fct_customer_by_watchlist

    echo "Running dbt test for fct_customer_by_watchlist..."
    dbt test --select fct_customer_by_watchlist

    echo "dbt transformation completed successfully."
    """

    t4 = BashOperator(
        task_id='run_dbt_transform',
        bash_command=t4_dbt_bash_command,
        dag=dag
    ) 

    t5 = BashOperator(
        task_id='run_dbt_transform_monthly',
        bash_command=t5_dbt_bash_command,
        dag=dag
    )
    t6 = BashOperator(
        task_id='run_dbt_transform_platform',
        bash_command=t6_dbt_bash_command,
        dag=dag
    )
    t7 = BashOperator(
        task_id='run_dbt_transform_watchlist',
        bash_command=t7_dbt_bash_command,
        dag=dag
    )  


    t1 = PythonOperator(
        task_id='extract_customer_data',
        python_callable=extract_customer_data,
    )
    t2 = PythonOperator(
        task_id='save_to_minio',
        python_callable=save_to_minio,
    )
    t3 = PythonOperator(
        task_id='load_to_postgres',
        python_callable=load_to_postgres,
    )
    # t4 = PythonOperator(
    #     task_id='run_dbt_transform',
    #     python_callable=run_dbt_transform,
    # )
    # t5 = PythonOperator(
    #     task_id='run_dbt_transform_monthly',
    #     python_callable=run_dbt_transform_monthly,
    # )
    # t6 = PythonOperator(
    #     task_id='run_dbt_transform_platform',
    #     python_callable=run_dbt_transform_platform,
    # )
    # t7 = PythonOperator(
    #     task_id='run_dbt_transform_watchlist',
    #     python_callable=run_dbt_transform_watchlist,
    # )

    # Define task dependencies
    t1 >> t2 >> t3 >> t4 >> t5 >> t6 >> t7
