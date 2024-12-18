# Automated App Testing

An automated testing framework for the Pagoda app using Appium and Python.

## Project Structure

```
automated-app-testing/
├── src/                    # Source code
│   ├── pagoda.py          # Main automation class
│   ├── api_searcher.py    # API search functionality
│   ├── request_replayer.py # Request replay utilities
│   └── run_automation.py  # Main entry point
├── assets/                # Image assets for UI recognition
│   ├── agree.png
│   ├── location.png
│   └── ...
├── config/               # Configuration files
│   └── config.py        # Project settings
├── data/                # Data files
│   ├── captured_requests.json
│   └── search_results.json
├── logs/                # Log files
│   └── requests.log
├── tests/               # Test files
├── requirements.txt     # Python dependencies
└── WORKFLOW.md         # Workflow documentation
```

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Appium server settings in `config/config.py`

3. Start the Appium server

## Usage

Run the automation:
```bash
python src/run_automation.py
```

See `WORKFLOW.md` for detailed process documentation.
