"""
PRUEBAS FUNCIONALES DE PUNTA A PUNTA a través de la interfaz web (Selenium).

Cada prueba es un caso de uso del usuario final, ejecutado en un Chrome real:
  CP-WEB-01  Login con credenciales incorrectas muestra un error
  CP-WEB-02  Login correcto muestra el mapa con los aeropuertos de Colombia
  CP-WEB-03  Clic en un aeropuerto del mapa muestra su detalle
  CP-WEB-04  Crear un itinerario lo agrega a la tabla
  CP-WEB-05  Regla de negocio: salida y llegada iguales -> mensaje de error
  CP-WEB-06  Editar un itinerario actualiza la tabla
  CP-WEB-07  Ver la ruta dibuja la línea salida -> llegada en el mapa
  CP-WEB-08  Eliminar un itinerario lo quita de la tabla
  CP-WEB-09  Cerrar sesión vuelve a la pantalla de login
"""
import uuid

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Nombre único para no chocar con datos de otras ejecuciones
USER_NAME = f"Selenium {uuid.uuid4().hex[:6]}"


# ----------------------------------------------------------------- utilidades
def login(driver, wait, username="viajero", password="viajero123"):
    form = driver.find_element(By.ID, "login-form")
    for name, value in (("username", username), ("password", password)):
        field = form.find_element(By.NAME, name)
        field.clear()
        field.send_keys(value)
    form.find_element(By.CSS_SELECTOR, "button[type=submit]").click()


def wait_until_app_loaded(driver, wait):
    wait.until(EC.visibility_of_element_located((By.ID, "app")))
    # El mapa está listo cuando Plotly tiene datos
    wait.until(lambda d: d.execute_script("const m=document.getElementById('map'); return m.data && m.data.length > 0"))
    wait.until(lambda d: len(Select(d.find_element(By.NAME, "departure_airport_id")).options) > 1)


def fill_itinerary(driver, user_name, departure_index, arrival_index, travel_date, minutes):
    form = driver.find_element(By.ID, "itinerary-form")
    name = form.find_element(By.NAME, "user_name")
    name.clear()
    name.send_keys(user_name)
    Select(form.find_element(By.NAME, "departure_airport_id")).select_by_index(departure_index)
    Select(form.find_element(By.NAME, "arrival_airport_id")).select_by_index(arrival_index)
    # El input type=date depende del idioma del navegador: se asigna el valor ISO por JavaScript
    driver.execute_script("arguments[0].value = arguments[1]", form.find_element(By.NAME, "travel_date"), travel_date)
    duration = form.find_element(By.NAME, "duration_minutes")
    duration.clear()
    duration.send_keys(str(minutes))
    form.find_element(By.CSS_SELECTOR, "button[type=submit]").click()


def row_of(driver, user_name):
    rows = driver.find_elements(By.XPATH, f"//tbody[@id='itinerary-rows']/tr[td[1][normalize-space()='{user_name}']]")
    return rows[0] if rows else None


def message_text(wait):
    box = wait.until(EC.visibility_of_element_located((By.ID, "message")))
    return box.text, box.get_attribute("class")


# ---------------------------------------------------------------------- casos
# Las pruebas 03-09 comparten la sesión del navegador y se ejecutan en orden.
def test_cp_web_01_login_incorrecto_muestra_error(home, wait):
    login(home, wait, password="clave-equivocada")
    alert = wait.until(EC.alert_is_present())
    text = alert.text
    alert.accept()
    assert "incorrectos" in text
    assert home.find_element(By.ID, "app").get_attribute("hidden") is not None


def test_cp_web_02_login_correcto_muestra_mapa_de_colombia(home, wait):
    login(home, wait)
    wait_until_app_loaded(home, wait)
    points = home.execute_script("return document.getElementById('map').data[0].lat.length")
    assert points >= 40  # API Colombia tiene ~50 aeropuertos con coordenadas
    # Todas las coordenadas deben quedar dentro de Colombia (el Adapter corrige lat/lon invertidas)
    lats = home.execute_script("return document.getElementById('map').data[0].lat")
    assert all(-5 <= lat <= 14 for lat in lats)


def test_cp_web_03_clic_en_aeropuerto_muestra_detalle(driver, wait):
    # Simula el evento plotly_click sobre el primer punto del mapa
    driver.execute_script(
        "const m=document.getElementById('map');"
        "m.emit('plotly_click', {points: [{customdata: m.data[0].customdata[0]}]});"
    )
    detail = wait.until(lambda d: d.find_element(By.ID, "airport-detail").text)
    assert "IATA" in detail and "OACI" in detail


def test_cp_web_04_crear_itinerario(driver, wait):
    fill_itinerary(driver, USER_NAME, 0, 1, "2027-06-15", 75)
    text, css = message_text(wait)
    assert "creado" in text and "error" not in css
    wait.until(lambda d: row_of(d, USER_NAME) is not None)
    assert "75 min" in row_of(driver, USER_NAME).text


def test_cp_web_05_salida_y_llegada_iguales_muestra_error(driver, wait):
    wait.until(EC.invisibility_of_element_located((By.ID, "message")))
    fill_itinerary(driver, "Regla de negocio", 2, 2, "2027-06-15", 30)
    text, css = message_text(wait)
    assert "error" in css
    assert "deben ser distintos" in text  # mensaje de la regla de negocio del dominio


def test_cp_web_06_editar_itinerario(driver, wait):
    row_of(driver, USER_NAME).find_element(By.XPATH, ".//button[text()='Editar']").click()
    wait.until(EC.text_to_be_present_in_element((By.ID, "form-title"), "Editar"))
    fill_itinerary(driver, USER_NAME, 0, 1, "2027-06-20", 120)
    wait.until(lambda d: row_of(d, USER_NAME) is not None and "120 min" in row_of(d, USER_NAME).text)
    assert "2027-06-20" in row_of(driver, USER_NAME).text


def test_cp_web_07_ver_ruta_en_el_mapa(driver, wait):
    row_of(driver, USER_NAME).find_element(By.XPATH, ".//button[text()='Ruta']").click()
    wait.until(lambda d: d.execute_script("return document.getElementById('map').data.length") == 2)
    route = driver.execute_script("return document.getElementById('map').data[1]")
    assert route["mode"] == "lines+markers" and "→" in route["name"]


def test_cp_web_08_eliminar_itinerario(driver, wait):
    row_of(driver, USER_NAME).find_element(By.XPATH, ".//button[text()='Eliminar']").click()
    wait.until(EC.alert_is_present()).accept()  # confirm("¿Eliminar este itinerario?")
    wait.until(lambda d: row_of(d, USER_NAME) is None)


def test_cp_web_09_cerrar_sesion(driver, wait):
    driver.find_element(By.XPATH, "//span[@id='session']/button").click()
    wait.until(EC.visibility_of_element_located((By.ID, "login-section")))
    assert driver.execute_script("return sessionStorage.getItem('token')") is None

