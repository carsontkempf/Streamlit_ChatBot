import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import subprocess
import os
import signal
from pathlib import Path
import pyperclip # Added for clipboard functionality


CHROME_DRIVER_PATH = '/usr/local/bin/chromedriver'
STREAMLIT_APP_URL = 'http://localhost:8501'
APP_DIRECTORY = Path(__file__).parent.parent

# Define locators for your Streamlit elements here
TEXT_AREA_LOCATOR = (By.CSS_SELECTOR, "textarea[aria-label='Enter your message:']")
SUBMIT_BUTTON_LOCATOR = (By.XPATH, "//button[.//p[text()='Submit']]")

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
    
    driver.implicitly_wait(2) # Implicit wait for elements to appear
    yield driver
    driver.quit()

def get_error_text_if_present(driver: webdriver.Chrome, start_phrase: str, end_phrase: str, timeout: int = 60) -> str | None:
    wait = WebDriverWait(driver, timeout)
    try:
        # Wait until the start_phrase is present in the body of the page
        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), start_phrase))
        
        # If we reach here, the start_phrase is present
        full_text = driver.find_element(By.TAG_NAME, 'body').text
        start_index = full_text.find(start_phrase)
        
        # This check is slightly redundant due to wait.until but ensures robustness
        if start_index != -1:
            search_from_index = start_index + len(start_phrase)
            end_index = full_text.find(end_phrase, search_from_index)
            
            if end_index != -1:
                extracted_text = full_text[start_index:end_index].rstrip()
                if extracted_text: # Ensure there's something to copy
                    pyperclip.copy(extracted_text)
                    print(f"\n\n\n\n\n--- Error text copied to clipboard. ---")
                return extracted_text

    except TimeoutException:
        return None

def test_fill_form_and_submit(streamlit_server, driver):

    driver.get(STREAMLIT_APP_URL)
    
    # Find the text area using the defined locator
    text_area = driver.find_element(*TEXT_AREA_LOCATOR)
    
    # Input the desired text
    text_area.send_keys("What is the weather like in Maryville, MO?")
    
    # Wait for 3 seconds after text input
    time.sleep(0.75)
    
    # Find the submit button and click it
    submit_button = driver.find_element(*SUBMIT_BUTTON_LOCATOR)
    submit_button.click()

    error_start_phrase = "Error:"
    error_end_phrase = "Ask Google"
    
    extracted_error_message = get_error_text_if_present(driver, error_start_phrase, error_end_phrase)

    if extracted_error_message:
        print("\n\n--- Application Error Detected ---\n\n")
        print(extracted_error_message) # Print the extracted error
        print("\n\n----------------------------------\n")
        pytest.fail(f"Test failed because streamlit returned an error.")
    else:
        print(f"\n--- No application error found. Test continues/passes. ---\n")

    print("--- Test execution finished (no critical error found), browser will remain open for a few seconds. ---\n")
    time.sleep(10)
