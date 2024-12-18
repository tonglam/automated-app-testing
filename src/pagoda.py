"""Module for automating product searches in the Pagoda mobile application using Appium."""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from appium.options.android.uiautomator2.base import UiAutomator2Options
from appium import webdriver

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config.config import *

class NavigationError(Exception):
    """Raised when navigation fails in the Pagoda app."""
    pass

class PagodaAPIError(Exception):
    """Raised when API requests fail in the Pagoda app."""
    pass

class PagodaSearch:
    """A class to handle product searches in the Pagoda mobile application using Appium automation."""

    def __init__(self, driver: RemoteWebDriver = None):
        """Initialize the PagodaSearch class with configuration."""
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        
        # Set up logging
        if not self.logger.handlers:
            handler = logging.FileHandler(LOGS_DIR / "automation.log")
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Set up HTTP request logging
        self.http_logger = logging.getLogger("http_requests")
        if not self.http_logger.handlers:
            http_handler = logging.FileHandler(LOGS_DIR / "requests.log")
            http_formatter = logging.Formatter("%(asctime)s - %(message)s")
            http_handler.setFormatter(http_formatter)
            self.http_logger.addHandler(http_handler)
            self.http_logger.setLevel(logging.INFO)

    def find_element_by_image(self, image_path, timeout=10, threshold=None):
        """Find a single element by image matching."""
        try:
            if self.driver is None:
                self.logger.error("WebDriver is not initialized. Please call start_automation() first.")
                return None
                
            image_path = str(ASSETS_DIR / image_path)
            if not os.path.exists(image_path):
                self.logger.error(f"Image file not found: {image_path}")
                return None
            
            # Try to find element by image recognition
            try:
                self.logger.info(f"Attempting to find image: {image_path}")
                element = WebDriverWait(self.driver, timeout).until(
                    lambda x: x.find_element(AppiumBy.IMAGE, image_path)
                )
                self.logger.info("Image element found successfully")
                return element
            except Exception as e:
                self.logger.debug(f"Image recognition failed: {str(e)}")
                return None

        except Exception as e:
            self.logger.error(f"Error finding image element: {str(e)}")
            return None

    def find_elements_by_image(self, image_path, timeout=10, max_retries=1):
        """Find multiple elements by image matching with retry logic."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.driver is None:
                    self.logger.error("WebDriver is not initialized. Please call start_automation() first.")
                    return []
                    
                image_path = str(ASSETS_DIR / image_path)
                if not os.path.exists(image_path):
                    self.logger.error(f"Image file not found: {image_path}")
                    return []
                    
                elements = WebDriverWait(self.driver, timeout).until(
                    lambda x: x.find_elements(AppiumBy.IMAGE, image_path)
                )
                if elements:
                    return elements
            except TimeoutException:
                self.logger.info(f"No elements found for image: {image_path}")
            except Exception as e:
                self.logger.error(f"Error finding elements: {str(e)}")
            
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(2)
        
        return []

    def handle_popups(self, max_attempts=1):
        """Handle any popups that appear during automation."""
        try:
            close_button = self.find_element_by_image("close_button.png", timeout=2)
            if close_button:
                self.logger.info("Found popup close button, clicking it")
                close_button.click()
                time.sleep(1)
        except Exception as e:
            self.logger.debug(f"No popup found or error handling popup: {str(e)}")
            pass

    def navigate_to_nationwide_delivery(self, max_attempts=3):
        """Navigate to the nationwide delivery section."""
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Navigation attempt {attempt + 1}/{max_attempts}")
                
                # Wait for the bottom navigation to be visible first
                try:
                    # Wait for the immediate delivery icon to be visible
                    WebDriverWait(self.driver, 10).until(
                        lambda x: x.find_element(AppiumBy.XPATH, "//android.widget.TextView[@text='及时达']")
                    )
                    self.logger.info("Bottom navigation is visible")
                    time.sleep(2)  # Give a moment for the entire UI to stabilize
                except Exception as e:
                    self.logger.warning(f"Bottom navigation not found: {str(e)}")
                    continue
                
                # Now try finding the nationwide delivery icon
                self.logger.info("Trying to find nationwide delivery by image...")
                icon = self.find_element_by_image("nationwide_delivery_icon.png", timeout=5)
                if icon:
                    icon.click()
                    time.sleep(2)
                    return True
                
                self.logger.warning("Nationwide delivery icon not found")
            except Exception as e:
                self.logger.warning(f"Error navigating to nationwide delivery: {str(e)}")
            
            if attempt < max_attempts - 1:
                time.sleep(2)
        
        self.logger.error("Failed to navigate to nationwide delivery after all attempts")
        return False

    def search_products(self, search_term):
        """Search for products using the given search term."""
        try:
            # Handle any popups before searching
            self.handle_popups()
            
            # Navigate to nationwide delivery section
            if not self.navigate_to_nationwide_delivery():
                raise NavigationError("Failed to navigate to nationwide delivery section")
            
            # Find and click search input
            search_input = self.find_element_by_image("search_input.png", timeout=10)
            if not search_input:
                raise NavigationError("Search input not found")
                
            search_input.click()
            time.sleep(2)
            
            # Enter search term
            if self.driver is None:
                self.logger.error("Driver is not initialized. Please call _setup_driver first.")
                return False
            search_field = self.driver.find_element(AppiumBy.CLASS_NAME, "android.widget.EditText")
            search_field.clear()
            search_field.send_keys(search_term + '\n')  # Enter key
            time.sleep(1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error during product search: {str(e)}")
            return False

    def start_automation(self):
        """Start the automation process."""
        try:
            self.logger.info("Starting automation process...")
            self._setup_driver()
            self.logger.info("Driver setup complete")
            
            # Handle startup dialogs
            self.handle_startup_dialogs()
            
            # Quick popup check
            self.handle_popups()
            
            # Wait for home page to be fully loaded
            self.logger.info("Waiting for home page to load...")
            try:
                # First wait for any TextView to appear
                WebDriverWait(self.driver, 10).until(
                    lambda x: len(x.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")) > 0
                )
                
                # Then wait a bit longer for the page to fully render
                time.sleep(5)  # Give more time for the home page to fully load
                
                self.logger.info("Home page is fully loaded")
            except Exception as e:
                self.logger.error(f"Home page load failed: {str(e)}")
                return False
            
            # Navigate to nationwide delivery
            if not self.navigate_to_nationwide_delivery():
                raise NavigationError("Failed to navigate to nationwide delivery section")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error during automation: {str(e)}")
            return False

    def handle_startup_dialogs(self):
        """Handle initial startup dialogs like agree and location selection."""
        try:
            # Check for agree button with short timeout
            agree_button = self.find_element_by_image("agree.png", timeout=2)
            if agree_button:
                self.logger.info("Found agree button, clicking it")
                agree_button.click()
                time.sleep(1)
            
            # Check for location selection with short timeout
            location_button = self.find_element_by_image("select_location.png", timeout=2)
            if location_button:
                self.logger.info("Found location selection button, clicking it")
                location_button.click()
                time.sleep(1)
                
                # Select specific location
                store_location = self.find_element_by_image("location.png", timeout=3)
                if store_location:
                    self.logger.info("Found store location, clicking it")
                    store_location.click()
                    time.sleep(1)
                
        except Exception as e:
            self.logger.debug(f"No startup dialogs found or error handling them: {str(e)}")
            pass

        self.logger.info("Startup dialog handling complete")

    def verify_app_ready(self):
        """Verify that the app is ready for automation."""
        try:
            WebDriverWait(self.driver, ELEMENT_WAIT).until(
                lambda x: x.find_element(AppiumBy.CLASS_NAME, "android.widget.ImageView")
            )
            self.logger.info("App UI elements verified")
            return True
        except Exception as e:
            self.logger.warning(f"Could not verify app UI elements: {str(e)}")
            return False

    def _setup_driver(self):
        """Set up and configure the Appium WebDriver."""
        # Clear UiAutomator2 server data
        self.logger.info("Clearing UiAutomator2 server data...")
        try:
            subprocess.run(['adb', 'shell', 'pm', 'clear', 'io.appium.uiautomator2.server'])
            subprocess.run(['adb', 'shell', 'pm', 'clear', 'io.appium.uiautomator2.server.test'])
        except Exception as e:
            self.logger.warning(f"Failed to clear UiAutomator2 server: {str(e)}")

        # Set up driver options
        options = UiAutomator2Options()
        options.platform_name = 'Android'
        options.automation_name = 'UiAutomator2'
        options.device_name = 'MuMu'
        options.app_package = APP_PACKAGE
        options.app_activity = APP_ACTIVITY
        options.no_reset = True

        # Initialize driver with retry mechanism
        max_retries = 3
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                self.logger.info(f"Attempting to initialize driver (attempt {retry_count + 1}/{max_retries})...")
                self.driver = webdriver.Remote(
                    command_executor=f'http://{APPIUM_HOST}:{APPIUM_PORT}',
                    options=options
                )
                self.logger.info("Driver initialization successful")
                
                # Configure driver settings
                self.driver.implicitly_wait(IMPLICIT_WAIT)
                time.sleep(INITIAL_WAIT)
                
                return
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Failed to initialize driver: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5)
                else:
                    self.logger.error("Max retries reached, failed to initialize driver")
                    raise WebDriverException(f"Failed to initialize driver after {max_retries} attempts: {str(last_error)}")

def main():
    """Main entry point for running the automation directly."""
    automation = PagodaSearch(webdriver.Remote(
        command_executor='http://localhost:4723',
        options=UiAutomator2Options()
    ))
    success = automation.start_automation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
