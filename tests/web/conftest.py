"""
Configuración de las pruebas de AUTOMATIZACIÓN WEB (Selenium).

El navegador Chrome corre en el contenedor "selenium" (perfil "tests" del
docker-compose) y abre el frontend a través del API Gateway, igual que un usuario.

    pytest (tu máquina) ──WebDriver──> Chrome (contenedor selenium) ──HTTP──> gateway ──> microservicios

Requisitos:
    docker compose up -d                              # sistema completo
    docker compose --profile tests up -d selenium     # navegador
    pip install -r tests/web/requirements.txt
    pytest tests/web -v

Ver el navegador en vivo: http://localhost:7900 (contraseña: secret)
"""
import os
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444")
# Dentro de la red de Docker el gateway se llama "gateway" y escucha en el puerto 80
BASE_URL = os.getenv("BASE_URL", "http://gateway")
EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "docs" / "pruebas" / "evidencias"


@pytest.fixture(scope="session")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1366,1000")
    options.add_argument("--lang=es-CO")
    browser = webdriver.Remote(command_executor=SELENIUM_URL, options=options)
    yield browser
    browser.quit()


@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 20)


@pytest.fixture(autouse=True)
def screenshot(request, driver):
    """Guarda una captura de pantalla al final de cada prueba (evidencia para el informe)."""
    yield
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(EVIDENCE_DIR / f"{request.node.name}.png"))


@pytest.fixture
def home(driver):
    """Abre el frontend con la sesión limpia."""
    driver.get(BASE_URL)
    driver.execute_script("sessionStorage.clear();")
    driver.get(BASE_URL)
    return driver
