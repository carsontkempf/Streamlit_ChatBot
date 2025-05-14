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
import psutil # Added for process management
import logging


# --- Configure Logging Levels for External Libraries ---
# Set higher logging levels for noisy libraries to reduce verbosity in test output.
# This affects the pytest runner's process where Selenium commands are issued.
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
# Optional: If other selenium parts are noisy, you can add them too:
# logging.getLogger("selenium.webdriver.common.service").setLevel(logging.WARNING)
# logging.getLogger("selenium.webdriver.common.driver_finder").setLevel(logging.WARNING)

CHROME_DRIVER_PATH = '/usr/local/bin/chromedriver'
STREAMLIT_APP_URL = 'http://localhost:8501'
APP_DIRECTORY = Path(__file__).parent.parent

# Define locators for your Streamlit elements here
TEXT_AREA_LOCATOR = (By.CSS_SELECTOR, "textarea[aria-label='Enter your message:']")
SUBMIT_BUTTON_LOCATOR = (By.XPATH, "//button[.//p[text()='Submit']]")

def pytest_exception_interact(node, call, report):
    """
    Hook called by pytest when an exception is raised and not handled by the test.
    This will copy the full traceback of Python exceptions to the clipboard.
    """
    if report.failed and hasattr(report, 'longreprtext') and report.longreprtext:
        # report.longreprtext contains the string representation of the traceback
        # This will capture tracebacks for unhandled Python exceptions.
        # For failures from pytest.fail(..., pytrace=False), longreprtext might be minimal,
        # which is fine as the UI error is handled separately.

        error_details_to_copy = f"Pytest Error Report for: {report.nodeid}\n"
        error_details_to_copy += f"Stage: {report.when} ({report.outcome})\n"
        error_details_to_copy += "\nFull Traceback:\n"
        error_details_to_copy += report.longreprtext

        try:
            pyperclip.copy(error_details_to_copy)
            print(f"\n--- Full Python exception traceback for {report.nodeid} copied to clipboard. ---")
        except pyperclip.PyperclipException as e:
            # This can happen in CI environments or if no clipboard utility is available
            print(f"\n--- Could not copy Python exception traceback to clipboard: {e} ---")

def kill_process_on_port(port: int):
    """Finds and terminates a process listening on the given port."""
    # Only fetch attributes that as_dict can handle directly.
    # We will call proc.connections() method separately.
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    print(f"--- Found process {proc.info['name']} (PID: {proc.info['pid']}) listening on port {port}. Terminating. ---")
                    try:
                        process_to_kill = psutil.Process(proc.info['pid'])
                        process_to_kill.terminate() # Send SIGTERM
                        process_to_kill.wait(timeout=3) # Wait for graceful termination
                        print(f"--- Process {proc.info['pid']} terminated. ---")
                    except psutil.NoSuchProcess:
                        print(f"--- Process {proc.info['pid']} already terminated. ---")
                    except psutil.TimeoutExpired:
                        print(f"--- Process {proc.info['pid']} did not terminate gracefully, killing. ---")
                        process_to_kill.kill() # Send SIGKILL
                        process_to_kill.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass # Process might have died or we don't have permissions

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
        # Kill any existing process on port 8501 before starting a new one
        kill_process_on_port(8501)

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
                if extracted_text:  # Ensure there's something to copy
                    try:
                        pyperclip.copy(extracted_text)
                        print(f"\n\n\n\n\n--- UI Error text copied to clipboard. ---")
                    except pyperclip.PyperclipException as e:
                        # This can happen in CI environments or if no clipboard utility is available
                        print(f"\n\n\n\n\n--- Could not copy UI error text to clipboard: {e} ---")
                return extracted_text

    except TimeoutException:
        return None

def test_fill_form_and_submit(streamlit_server, driver):

    driver.get(STREAMLIT_APP_URL)

    error_start_phrase = "Error:"
    error_end_phrase = "Ask Google" # Or another phrase that reliably ends your error messages

    # Initial check for errors on page load
    initial_error_message = get_error_text_if_present(driver, error_start_phrase, error_end_phrase, timeout=2) # Shorter timeout for initial check
    if initial_error_message:
        print("\n\n--- Application Error Detected on Page Load ---\n\n")
        print(initial_error_message)
        print("\n\n---------------------------------------------\n")
        pytest.fail(f"Test failed because Streamlit app showed an error on initial load: {initial_error_message}", pytrace=False)
    
    # Find the text area using the defined locator
    text_area = WebDriverWait(driver, 10).until(EC.presence_of_element_located(TEXT_AREA_LOCATOR))
    
    # Input the desired text
    text_area.send_keys("What is the weather like in Maryville, MO?")
    
    # Wait for 3 seconds after text input
    time.sleep(0.75)
    
    # Find the submit button and click it
    submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(SUBMIT_BUTTON_LOCATOR))
    submit_button.click()

    # Check for errors *after* submission
    post_submission_error_message = get_error_text_if_present(driver, error_start_phrase, error_end_phrase)

    if post_submission_error_message:
        print("\n\n--- Application Error Detected After Submission ---\n\n")
        print(post_submission_error_message)
        print("\n\n-------------------------------------------------\n")
        pytest.fail(f"Test failed because Streamlit returned an error after submission: {post_submission_error_message}", pytrace=False)
    else:
        # Additional check for "No tool invocation steps to graph."
        # This check should happen if no explicit "Error:" was found by get_error_text_if_present
        # We need to wait a bit for the page to potentially update with the final output.
        no_tools_phrase = "No tool invocation steps to graph."
        # Using a robust XPATH to find the phrase anywhere on the page, ignoring whitespace issues.
        no_tools_locator = (By.XPATH, f"//*[contains(normalize-space(.), '{no_tools_phrase.strip()}')]")
        
        # Increased timeout for this specific check, as this message might take time to appear.
        wait_for_no_tools_text = WebDriverWait(driver, 20) # Wait up to 20 seconds

        try:
            # Check if the "no tools" phrase appears within the timeout
            element_found = wait_for_no_tools_text.until(
                EC.presence_of_element_located(no_tools_locator)
            )
            # If we reach here, an element containing the phrase was found.
            error_message = f"Critical Error: Found phrase '{no_tools_phrase.strip()}' indicating no tools were used."
            print(f"\n\n--- TEST FAILURE: {error_message} ---\n\n")
            print(f"The application displayed a message indicating that no tool invocation steps were available to graph.")
            print("\n\n-----------------------------------------------------------------------\n")
            pytest.fail(error_message, pytrace=False)
        except TimeoutException:
            # The phrase "No tool invocation steps to graph." did NOT appear within the timeout.
            # This means tools were likely used, or at least this specific negative indicator wasn't present.
            print(f"\n--- Phrase '{no_tools_phrase.strip()}' not found. Test proceeds assuming tools were invoked or this message was not expected. ---\n")

    print("--- Test execution finished (no critical error found), browser will remain open for a few seconds. ---\n")
    time.sleep(20)
