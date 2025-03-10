import boto3
import requests
import time
from datetime import datetime
from requests.exceptions import RequestException


S3_BUCKET = "zappa-8jwijavgz"


def download_html():
    url = "https://casas.mitula.com.co/casas/bogota"
    s3 = boto3.client("s3")
    today = datetime.today().strftime('%Y-%m-%d')
    session = requests.Session()  # Mantener cookies y mejorar persistencia

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/",
    }

    for i in range(1, 11):  # Descargar 10 páginas
        attempt = 0
        while attempt < 3:  # Reintentos en caso de fallo
            try:
                response = session.get(f"{url}?page={i}", headers=headers, timeout=10)
                response.raise_for_status()  # Lanza error si el código no es 200 OK

                file_name = f"{today}-page{i}.html"
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=f"{today}/{file_name}",
                    Body=response.text.encode("utf-8"),  # Convertir a bytes
                    ContentType="text/html"
                )
                print(f"✅ Guardado en S3: s3://{S3_BUCKET}/{today}/{file_name}")
                break  # Salir del loop si todo está bien

            except RequestException as e:
                attempt += 1
                print(f"⚠ Error en página {i}, intento {attempt}: {e}")
                time.sleep(2 ** attempt)  # Espera exponencial: 2s, 4s, 8s

        if attempt == 3:
            print(f"❌ Falló la descarga de la página {i} después de 3 intentos")

    return {"status": "ok"}


def lambda_handler(event, context):
    return download_html()
