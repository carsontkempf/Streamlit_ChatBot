import subprocess
from subprocess import DEVNULL
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope="module")
def app_server():
    # Start the Streamlit app
    proc = subprocess.Popen(
        ["streamlit", "run", "app.py", "--server.headless", "true"],
        stdout=DEVNULL,
        stderr=DEVNULL
    )
    time.sleep(5)  # wait for server to start
    yield
    proc.terminate()
    proc.wait()

@pytest.fixture
def browser(app_server):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # Use ChromeDriver via webdriver-manager
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    yield driver
    driver.quit()

def test_ui_input(browser):
    browser.get("http://localhost:8501")
    # wait for the input box to appear and become interactive
    chat_box = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox']"))
    )
    chat_box.click()
    chat_box.send_keys("Hello Streamlit!")

    button = browser.find_element(By.TAG_NAME, "button")
    button.click()

    # keep the browser open so you can watch
    time.sleep(60)
    assert True
