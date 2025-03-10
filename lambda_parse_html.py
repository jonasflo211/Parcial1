import boto3
import csv
import json
from bs4 import BeautifulSoup
from datetime import datetime

# Buckets S3
S3_BUCKET_INPUT = "zappa-8jwijavgz"  # Bucket de entrada
S3_BUCKET_OUTPUT = "zappa-casas-oo-1000"  # Bucket de salida

def clean_price(price_str):
    """Limpia el precio eliminando símbolos y separadores."""
    if not price_str:
        return "N/A"
    price_str = price_str.replace("COP", "").replace("$", "").replace(".", "").strip()
    return price_str

def extract_data_from_html(html_content):
    """Extrae datos de listados desde HTML o JSON dentro del HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    listings = []
    today = datetime.today().strftime('%Y-%m-%d')

    # Intentar extraer datos desde JSON-LD si existe
    script_tag = soup.find("script", type="application/ld+json")
    if script_tag:
        try:
            data = json.loads(script_tag.string)
            properties = data[0].get('about', []) if isinstance(data, list) and data else []
            
            for prop in properties:
                address = prop.get('address', {})
                barrio = address.get('streetAddress', 'N/A').split(',')[0].strip()
                description = prop.get('description', '')
                valor_raw = description.split('$')[-1].split('\n')[0].strip() if '$' in description else 'N/A'
                valor = clean_price(valor_raw)
                
                habitaciones = prop.get("numberOfBedrooms", "N/A")
                banos = prop.get("numberOfBathroomsTotal", "N/A")
                mts2 = prop.get("floorSize", {}).get("value", "N/A")

                listings.append([today, barrio, valor, habitaciones, banos, mts2])
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error procesando JSON: {str(e)}")

    # Intentar extraer datos desde HTML si no hay JSON-LD
    if not listings:
        for listing in soup.select(".listing-item"):  # Ajusta el selector según la web real
            try:
                barrio = listing.select_one(".listing-location").text.strip() if listing.select_one(".listing-location") else "N/A"
                valor = clean_price(listing.select_one(".listing-price").text.strip()) if listing.select_one(".listing-price") else "N/A"
                num_habitaciones = listing.select_one(".listing-rooms").text.strip() if listing.select_one(".listing-rooms") else "N/A"
                num_banos = listing.select_one(".listing-bathrooms").text.strip() if listing.select_one(".listing-bathrooms") else "N/A"
                mts2 = listing.select_one(".listing-area").text.strip() if listing.select_one(".listing-area") else "N/A"
                
                listings.append([today, barrio, valor, num_habitaciones, num_banos, mts2])
            except Exception as e:
                print(f"⚠️ Error procesando una propiedad: {e}")

    return listings

def process_html_file(bucket, key):
    """Procesa un archivo HTML de S3, extrae los datos y los guarda como CSV."""
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    html_content = response["Body"].read().decode("utf-8")

    data = extract_data_from_html(html_content)
    if not data:
        print(f"❌ No se encontraron propiedades en {key}")
        return

    today = datetime.today().strftime('%Y-%m-%d')
    output_key = f"{today}/{today}.csv"
    temp_file = f"/tmp/{today}.csv"

    with open(temp_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["FechaDescarga", "Barrio", "Valor", "NumHabitaciones", "NumBanos", "mts2"])
        writer.writerows(data)

    s3.upload_file(temp_file, S3_BUCKET_OUTPUT, output_key)
    print(f"✅ CSV guardado en s3://{S3_BUCKET_OUTPUT}/{output_key}")

def lambda_handler(event, context):
    """Manejador de eventos Lambda que se activa cuando se sube un archivo HTML a S3."""
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        print(f"📥 Procesando archivo: s3://{bucket}/{key}")
        process_html_file(bucket, key)

    return {"statusCode": 200, "body": "Procesamiento completado"}
