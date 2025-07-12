import anthropic
import logging
from typing import Dict, Any, Optional
from app.config import settings
import asyncio
import time

# Set up logging
logger = logging.getLogger(__name__)

class AnthropicService:
    def __init__(self):
        logger.info("Initializing AnthropicService")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        self.temperature = settings.anthropic_temperature
        logger.info(f"AnthropicService initialized with model={self.model}, max_tokens={self.max_tokens}")
    
    async def generate_activity(self, prompt: str) -> Dict[str, Any]:
        """
        Generate an activity using Anthropic's Claude API
        """
        logger.info(f"Generating activity with prompt length: {len(prompt)}")
        try:
            logger.info("Making API call to Anthropic")
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            logger.info(f"API call successful, response length: {len(response.content[0].text)}")
            return {
                "success": True,
                "content": response.content[0].text,
                "model": self.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"API call failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    async def generate_activity_with_retry(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Generate activity with retry logic and kid-friendly waiting messages
        """
        for attempt in range(max_retries):
            if attempt > 0:
                # Kid-friendly waiting message
                waiting_messages = [
                    "Do 10 jumping jacks while we create your activity!",
                    "Take 5 deep breaths while we prepare something amazing!",
                    "Do a little dance while we get your activity ready!",
                    "Count to 20 while we make something special for you!"
                ]
                await asyncio.sleep(2)  # Brief pause between retries
            
            result = await self.generate_activity(prompt)
            if result["success"]:
                return result
        
        # If all retries failed
        return {
            "success": False,
            "error": "Unable to generate activity after multiple attempts",
            "content": None
        } 