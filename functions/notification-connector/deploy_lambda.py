"""
Despliega (o vuelve a desplegar) SendNotificationFunction en LocalStack.
Equivale a:  awslocal lambda create-function --function-name ... --zip-file fileb://function.zip
"""
import os
import time
import urllib.request
from pathlib import Path

import boto3

LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localhost:4566")
FUNCTION_NAME = os.getenv("FUNCTION_NAME", "SendNotificationFunction")
ZIP_PATH = os.getenv("FUNCTION_ZIP", "/function.zip")

# Región y credenciales: variables AWS_DEFAULT_REGION / AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
client = boto3.client("lambda", endpoint_url=LOCALSTACK_URL)


def wait_for_localstack(max_attempts: int = 60) -> None:
    for _ in range(max_attempts):
        try:
            urllib.request.urlopen(f"{LOCALSTACK_URL}/_localstack/health", timeout=3)
            return
        except OSError:
            print("Esperando a LocalStack...")
            time.sleep(2)
    raise RuntimeError("LocalStack no respondió")


def deploy() -> None:
    wait_for_localstack()
    code = Path(ZIP_PATH).read_bytes()
    environment = {
        "Variables": {
            "DB_HOST": os.environ["DB_HOST"],
            "DB_PORT": os.environ.get("DB_PORT", "5432"),
            "DB_NAME": os.environ["DB_NAME"],
            "DB_USER": os.environ["DB_USER"],
            "DB_PASSWORD": os.environ["DB_PASSWORD"],
        }
    }

    # Si ya existía (reinicio del contenedor), la borramos y creamos de nuevo.
    try:
        client.delete_function(FunctionName=FUNCTION_NAME)
    except client.exceptions.ResourceNotFoundException:
        pass

    client.create_function(
        FunctionName=FUNCTION_NAME,
        Runtime="python3.12",
        Role="arn:aws:iam::000000000000:role/lambda-role",  # LocalStack no valida IAM
        Handler="handler.handler",
        Code={"ZipFile": code},
        Environment=environment,
        Timeout=30,
    )
    client.get_waiter("function_active_v2").wait(FunctionName=FUNCTION_NAME)
    print(f"Lambda {FUNCTION_NAME} desplegada en LocalStack")


if __name__ == "__main__":
    deploy()
