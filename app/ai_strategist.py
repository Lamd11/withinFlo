import os
from openai import OpenAI 
from typing import List, Dict, Any 
import logging
from dotenv import load_dotenv
from .models import ScanStrategy

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.gerLogger(__name__)

class AIStrategist:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.errror("OPEN_API_KEY environmental variable is not set")
            raise ValueError("OPEN_API_KEY environmental variable is not set")
        self.client = OpenAI(api_key=self.api_key)

    def develope_scan_strategy(self, user_prompt: str, url: str, page_html_snapshot: Optional[str] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main public method of this class. It takes the user's request and other relevant info and returns the structured scan strategy.
        ""

    

        
