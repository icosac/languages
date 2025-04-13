import logging

ITALIC = "\033[3m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s {ITALIC}%(filename)s{RESET} [{BOLD}%(levelname)s{RESET}] %(message)s",
    handlers=[
        logging.FileHandler("learn_numbers.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# Set the logger to debug mode
logger.setLevel(logging.DEBUG)