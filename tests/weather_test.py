import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
import time
import subprocess
import os
import signal
from pathlib import Path


CHROME_DRIVER_PATH = '/usr/local/bin/chromedriver'
STREAMLIT_APP_URL = 'http://localhost:8501'
APP_DIRECTORY = Path(__file__).parent.parent

# Define locators for your Streamlit elements here
# Example: TEXTBOX_LOCATOR = (By.ID, "my_streamlit_textbox_id")
# Example: SUBMIT_BUTTON_LOCATOR = (By.XPATH, '//button[contains(text(),"Submit")]')

@pytest.fixture(scope="session") # Run once per test session
def streamlit_server():
    """Fixture to start and stop the Streamlit server."""
    command = [
        "streamlit", "run", "app.py",
        "--server.headless", "true",
        "--server.port", "8501"
    ]
    
    process = None
    try:
        # Start the Streamlit server as a subprocess
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=APP_DIRECTORY, preexec_fn=os.setsid)
        
        time.sleep(5) 

        if process.poll() is not None:
            # Capture stdout and stderr for debugging
            stdout, stderr = process.communicate() # Reads all output and waits for process to terminate
            error_message = f"Streamlit server failed to start. Return code: {process.returncode}\n"
            if stdout:
                error_message += f"Stdout:\n{stdout.decode(errors='replace')}\n"
            if stderr:
                error_message += f"Stderr:\n{stderr.decode(errors='replace')}\n"
            raise RuntimeError(
                error_message
            )
        
        yield process 
        
    finally:
        if process and process.poll() is None: # Check if process is still running
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
            except Exception:
                # Process might still be running.
                pass

            if process.poll() is None:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    process.wait(timeout=5)  # Crucial: wait for SIGKILL to take effect
                except ProcessLookupError:
                    pass
                except Exception:
                    pass

@pytest.fixture
def driver():
    service = ChromeService(executable_path=CHROME_DRIVER_PATH)
    options = ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.implicitly_wait(10) # Implicit wait for elements to appear
    yield driver
    driver.quit()

def test_fill_form_and_submit(streamlit_server, driver):
    """
    Test to open the Streamlit app and keep it open for 30 seconds.
    Future steps will involve form filling and submission.
    """
    driver.get(STREAMLIT_APP_URL)
    
    # Wait for 30 seconds as requested, to observe the page
    time.sleep(30)
    
    # In future steps, you would add interactions here:
    # text_area = driver.find_element(*TEXT_AREA_LOCATOR)
    # text_area.send_keys("Hello Streamlit")
    # submit_button = driver.find_element(*SUBMIT_BUTTON_LOCATOR)
    # submit_button.click()
    # ... and assertions