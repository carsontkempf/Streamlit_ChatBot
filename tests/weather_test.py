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
import pyperclip
import psutil
import logging
import threading # Added for subprocess output streaming
import sys # Added for flushing output


logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("selenium.webdriver.common.service").setLevel(logging.WARNING)
logging.getLogger("selenium.webdriver.common.driver_finder").setLevel(logging.WARNING)

CHROME_DRIVER_PATH = '/usr/local/bin/chromedriver'
STREAMLIT_APP_URL = 'http://localhost:8501'
APP_DIRECTORY = Path(__file__).parent.parent

# Define locators for your Streamlit elements here
TEXT_AREA_LOCATOR = (By.CSS_SELECTOR, "textarea[aria-label='Enter your message:']")
SUBMIT_BUTTON_LOCATOR = (By.XPATH, "//button[.//p[text()='Submit']]")


def kill_process_on_port(port: int):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    print(f"--- Found process {proc.info['name']} (PID: {proc.info['pid']}) listening on port {port}. Terminating. ---")
                    try:
                        process_to_kill = psutil.Process(proc.info['pid'])
                        process_to_kill.terminate()
                        process_to_kill.wait(timeout=3)
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.TimeoutExpired:
                        process_to_kill.kill()
                        process_to_kill.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

# Function to stream subprocess output
def stream_output(pipe, prefix=""):
    try:
        for line in iter(pipe.readline, b''):
            print(f"{prefix}{line.decode(errors='replace').strip()}", flush=True) # Ensure immediate printing
    except Exception as e:
        print(f"{prefix}Error streaming output: {e}", flush=True)
    finally:
        if hasattr(pipe, 'close') and not pipe.closed:
            pipe.close()

@pytest.fixture(scope="session") # Run once per test session
def streamlit_server():
    command = [
        "streamlit", "run", "app.py",
        "--server.headless", "true",
        "--server.port", "8501"
    ]
    
    process = None # Initialize process to None
    stdout_thread = None
    stderr_thread = None

    try:
        kill_process_on_port(8501)
        print(f"\n--- [pytest fixture streamlit_server] Attempting to start Streamlit server with command: {' '.join(command)} ---", flush=True)
        # Start the Streamlit server as a subprocess
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            cwd=APP_DIRECTORY, 
            preexec_fn=os.setsid,
            bufsize=1,  # Line buffered
            universal_newlines=False # Keep as bytes for readline to work correctly with iter
        )
        
        # Start threads to stream stdout and stderr
        # Pass sys.stdout directly if you want to bypass pytest's per-test capture for these streams
        # However, printing with a prefix is generally better for distinguishing logs.
        stdout_thread = threading.Thread(target=stream_output, args=(process.stdout, "STREAMLIT_STDOUT: "), daemon=True)
        stderr_thread = threading.Thread(target=stream_output, args=(process.stderr, "STREAMLIT_STDERR: "), daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        print("--- [pytest fixture streamlit_server] Waiting for Streamlit server to initialize (5s)... ---", flush=True)
        time.sleep(5) # Give server time to start

        if process.poll() is not None:
            # Server failed to start, threads might have printed some output already
            error_message = f"Streamlit server failed to start. Return code: {process.returncode}\n"
            # stdout and stderr are being streamed by threads.
            print(f"--- [pytest fixture streamlit_server] {error_message} ---", flush=True)
            raise RuntimeError(
                error_message
            )
        print("--- [pytest fixture streamlit_server] Streamlit server presumed started. Yielding process. ---", flush=True)
        yield process 
        print("--- [pytest fixture streamlit_server] Test session finished. Cleaning up Streamlit server. ---", flush=True)

    finally:
        if process and process.poll() is None: # Check if process is still running
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=2) # Reduced timeout for SIGTERM
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
            except Exception:
                # Process might still be running.
                pass

            if process.poll() is None: # Check again if SIGTERM worked
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    process.wait(timeout=1)  # Reduced timeout for SIGKILL
                except ProcessLookupError:
                    pass
                except Exception:
                    pass
        
        # Wait for streaming threads to finish by joining them
        if stdout_thread and stdout_thread.is_alive():
            stdout_thread.join(timeout=2) # Add timeout to join
        if stderr_thread and stderr_thread.is_alive():
            stderr_thread.join(timeout=2) # Add timeout to join
        print("--- [pytest fixture streamlit_server] Cleanup complete. ---", flush=True)

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
        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), start_phrase))
        
        # If we reach here, the start_phrase is present
        full_text = driver.find_element(By.TAG_NAME, 'body').text
        start_index = full_text.find(start_phrase)
        
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
    error_end_phrase = "Ask Google"

    # Initial check for errors on page load
    initial_error_message = get_error_text_if_present(driver, error_start_phrase, error_end_phrase, timeout=2) # Shorter timeout for initial check
    if initial_error_message:
        print("\n\n--- Application Error Detected on Page Load ---\n\n")
        print(initial_error_message)
        print("\n\n---------------------------------------------\n")
        pytest.fail(f"Test failed because Streamlit app showed an error on initial load: {initial_error_message}", pytrace=False)
    
    # Find the text area using the defined locator
    text_area = WebDriverWait(driver, 10).until(EC.presence_of_element_located(TEXT_AREA_LOCATOR))
    
    text_area.send_keys("What is the weather like in Maryville, MO?")
    
    time.sleep(0.75)
    
    # Find the submit button and click it
    submit_button = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(SUBMIT_BUTTON_LOCATOR))
    submit_button.click()

    post_submission_error_message = get_error_text_if_present(driver, error_start_phrase, error_end_phrase, timeout=5) # Reduced timeout to 5 seconds

    if post_submission_error_message:
        print("\n\n--- Application Error Detected After Submission ---\n\n")
        print(post_submission_error_message)
        print("\n\n-------------------------------------------------\n")
        pytest.fail(f"Test failed because Streamlit returned an error after submission: {post_submission_error_message}", pytrace=False)
    else:
        no_tools_phrase = "No tool invocation steps to graph."
        
        caption_paragraph_locator = (By.XPATH, "//div[@data-testid='stCaptionContainer']/p")
        
        # Poll for the specific phrase for up to 15 seconds.
        wait_for_no_tools_text = WebDriverWait(driver, 15)

        try:
            wait_for_no_tools_text.until(
                EC.text_to_be_present_in_element(caption_paragraph_locator, no_tools_phrase.strip())
            )
            # If the above line does not raise a TimeoutException, the phrase was found.
            error_message = f"Critical Error: Found phrase '{no_tools_phrase.strip()}' indicating no tools were used."
            pytest.fail(error_message, pytrace=False) # Instantly terminate and fail the test
        except TimeoutException:
            print(f"\n--- Phrase '{no_tools_phrase.strip()}' not found. Test proceeds assuming tools were invoked or this message was not expected. ---\n")

    print("--- Test execution finished (no critical error found), browser will remain open for a few seconds. ---\n")
    time.sleep(20)
