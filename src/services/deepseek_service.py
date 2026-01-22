"""DeepSeek LLM service for reasoning and text generation."""

import json
import re
import time
from typing import Optional
from openai import OpenAI


class DeepSeekService:
    """Service wrapper for DeepSeek API via OpenAI SDK."""
    
    BASE_URL = "https://api.deepseek.com"
    
    def __init__(
        self,
        api_key: str,
        reasoning_model: str = "deepseek-reasoner",
        drafting_model: str = "deepseek-chat"
    ):
        """
        Initialize DeepSeek service.
        
        Args:
            api_key: DeepSeek API key
            reasoning_model: Model for reasoning tasks (R1)
            drafting_model: Model for drafting tasks (V3)
        """
        self.api_key = api_key
        self.reasoning_model = reasoning_model
        self.drafting_model = drafting_model
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """Lazy-initialize OpenAI client configured for DeepSeek."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("DeepSeek API key is required")
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL
            )
        return self._client
    
    def _call_model(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        Make a call to a DeepSeek model.
        
        Args:
            model: Model identifier
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Model response text
        """
        print(f"[DeepSeek] Calling {model} (temp={temperature}, max_tokens={max_tokens})")
        print(f"[DeepSeek] System prompt: {system_prompt[:100]}...")
        print(f"[DeepSeek] User prompt: {user_prompt[:100]}...")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            print(f"[DeepSeek] Got response: {len(content)} chars")
            return content
            
        except Exception as e:
            # Sanitize error message to avoid exposing API keys
            error_msg = str(e).replace(self.api_key, "***API_KEY***") if self.api_key else str(e)
            print(f"[DeepSeek] ERROR: {error_msg}")
            raise Exception(f"DeepSeek API error: {error_msg}")
    
    def call_r1(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3  # Lower temp for reasoning
    ) -> str:
        """
        Call DeepSeek R1 (reasoning model) for analysis tasks.
        
        Args:
            system_prompt: System prompt with analysis instructions
            user_prompt: User prompt with data to analyze
            temperature: Sampling temperature (default lower for consistency)
            
        Returns:
            Model response (should be JSON)
        """
        return self._call_model(
            model=self.reasoning_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=4096
        )
    
    def call_v3(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7  # Higher temp for creativity
    ) -> str:
        """
        Call DeepSeek V3 (chat model) for drafting tasks.
        
        Args:
            system_prompt: System prompt with drafting instructions
            user_prompt: User prompt with context
            temperature: Sampling temperature (default higher for creativity)
            
        Returns:
            Model response (should be JSON)
        """
        return self._call_model(
            model=self.drafting_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=4096
        )
    
    def call_with_retry(
        self,
        call_fn: callable,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 2,
        delay: float = 1.0
    ) -> str:
        """
        Call model with automatic retry on failure.
        
        Args:
            call_fn: Function to call (call_r1 or call_v3)
            system_prompt: System prompt
            user_prompt: User prompt
            max_retries: Maximum retry attempts
            delay: Delay between retries
            
        Returns:
            Model response
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return call_fn(system_prompt, user_prompt)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
        
        raise last_error
    
    @staticmethod
    def extract_json(text: str) -> dict:
        """
        Extract JSON from model response, handling common issues.
        
        Args:
            text: Raw model response
            
        Returns:
            Parsed JSON dict
        """
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array in text
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")
    
    def call_r1_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 2
    ) -> dict:
        """
        Call R1 and parse JSON response with retry.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_retries: Maximum retry attempts
            
        Returns:
            Parsed JSON dict
        """
        for attempt in range(max_retries + 1):
            try:
                response = self.call_r1(system_prompt, user_prompt)
                return self.extract_json(response)
            except (json.JSONDecodeError, ValueError) as e:
                if attempt == max_retries:
                    raise
                time.sleep(1.0)
    
    def call_v3_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 2
    ) -> dict:
        """
        Call V3 and parse JSON response with retry.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_retries: Maximum retry attempts
            
        Returns:
            Parsed JSON dict
        """
        for attempt in range(max_retries + 1):
            try:
                response = self.call_v3(system_prompt, user_prompt)
                return self.extract_json(response)
            except (json.JSONDecodeError, ValueError) as e:
                if attempt == max_retries:
                    raise
                time.sleep(1.0)
