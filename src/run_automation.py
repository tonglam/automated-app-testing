"""
Main entry point for the Pagoda app automation process.
This script orchestrates the execution of prerequisite checks and the main automation process.
"""

import os
import sys
import logging
import time
import threading
import socket
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config.config import *
from src.pagoda import PagodaSearch
from src.check_prerequisites import PrerequisitesChecker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def start_automation_workflow():
    """Start the main automation workflow."""
    checker = PrerequisitesChecker()
    try:
        # Step 1: Run all prerequisite checks
        logger.info("Step 1: Running prerequisite checks...")
        if not checker.prepare_for_pagoda():
            logger.error("Failed to prepare environment. Please fix the issues above.")
            return False
            
        # Step 2: Run Pagoda automation
        logger.info("Step 2: Starting Pagoda automation...")
        pagoda = PagodaSearch()
        try:
            pagoda.start_automation()
        finally:
            if pagoda.driver:
                try:
                    pagoda.driver.quit()
                except:
                    pass
        
        logger.info("Automation workflow completed successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Error in automation workflow: {str(e)}")
        return False
    finally:
        # Cleanup resources
        checker.cleanup()

if __name__ == "__main__":
    success = start_automation_workflow()
    sys.exit(0 if success else 1)
