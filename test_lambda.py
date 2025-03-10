import pytest
from unittest.mock import patch, MagicMock
from lambda_parse_html import extract_data_from_html, process_html_file
from main import download_html
import requests  # Se añade la importación correcta para requests


@pytest.mark.parametrize(
    "html_content, expected_output",
    [
        (
            """<script type='application/ld+json'>
            [{"about": [{"address": {"streetAddress": "Chapinero, Bogotá"},
            "description": "Apartamento $200000000", "numberOfBedrooms": 2,
            "numberOfBathroomsTotal": 1, "floorSize": {"value": 60}}]}]
            </script>""",
            [["2025-03-10", "Chapinero", "200000000", 2, 1, 60]],
        ),
        (
            """<div class='listing-item'>
              <div class='listing-location'>Chapinero</div>
              <div class='listing-price'>$200.000.000</div>
              <div class='listing-rooms'>2</div>
              <div class='listing-bathrooms'>1</div>
              <div class='listing-area'>60</div>
          </div>""",
            [["2025-03-10", "Chapinero", "200000000", "2", "1", "60"]],
        ),
        ("<html><body>No data</body></html>", []),
    ],
)
def test_extract_data_from_html(html_content, expected_output):
    """Prueba la extracción de datos desde HTML."""
    result = extract_data_from_html(html_content)
    assert result == expected_output


@patch("main.boto3.client")
def test_process_html_file(mock_boto):
    """Prueba el procesamiento de un archivo HTML desde S3."""
    mock_s3 = MagicMock()
    mock_boto.return_value = mock_s3

    mock_s3.get_object.return_value = {
        "Body": MagicMock(
            read=lambda: (
                b"<div class='listing-item'>"
                b"<div class='listing-location'>Chapinero</div>"
                b"</div>"
            )
        )
    }

    with patch("builtins.open", MagicMock()):
        process_html_file("test-bucket", "test-key")

    mock_s3.upload_file.assert_called_once()


def test_download_html_success():
    """Prueba que la descarga de HTML desde la web funciona correctamente."""
    with patch("main.requests.Session.get") as mock_get, \
         patch("main.boto3.client") as mock_boto:

        # Simular respuesta exitosa de requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Mock Page</html>"
        mock_get.return_value = mock_response

        # Simular cliente S3
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        result = download_html()

        # Verificar que se hicieron 10 llamadas a requests
        assert mock_get.call_count == 10
        # Verificar que se subieron 10 archivos a S3
        assert mock_s3.put_object.call_count == 10
        assert result["status"] == "ok"


def test_download_html_failure():
    """Prueba que la función maneja correctamente fallos en la descarga."""
    with patch(
        "main.requests.Session.get",
        side_effect=requests.RequestException("Request failed"),
    ), patch("main.boto3.client") as mock_boto, \
            patch("time.sleep", return_value=None):

        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        result = download_html()

        # Verificar que no se subieron archivos a S3
        assert mock_s3.put_object.call_count == 0
        # La función debe manejar errores sin fallar
        assert result["status"] == "ok"
