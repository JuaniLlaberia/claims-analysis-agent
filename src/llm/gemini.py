import os
from langchain_google_genai import (ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold)
from pydantic import BaseModel

class Gemini:
    """
    Light wrapper for one or more `ChatGoogleGenerativeAI` model instances.
    """
    def __init__(self,
                 temperature: float = 0.05,
                 top_p: float = 0.3,
                 top_k: int = 10) -> None:
        """
        Initializes Gemini class instance

        Args:
            temperature (float): Controls the randomness of the output.
            top_p (float): Lowering top_p narrows the field of possible tokens.
            top_k (int): Limits the token selection to the top_k most likely tokens at each step.
        """
        # Model hyperparameters
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.model_name = os.getenv("GEMINI_MODEL")
        self.google_api_key = os.getenv("GOOGLE_GEMINI_KEY")

        if not self.model_name:
            raise Exception("Failed to initialize Gemini model: Missing GEMINI_MODEL env. variable (model name).")

        if not self.google_api_key:
            raise Exception("Failed to initialize Gemini model: Missing GOOGLE_GEMINI_KEY env. variable (api key).")
        
        self.llm = self._create_model(api_key=self.google_api_key)

    def _create_model(self, api_key: str) -> ChatGoogleGenerativeAI:
        """
        Initializes and returns a ChatGoogleGenerativeAI model with customizable
        generation settings.

        Args:
            api_key (str): The Google API key.
        Returns:
            ChatGoogleGenerativeAI: An instance of the initialized model.
        """
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=api_key,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            })

    def invoke_model(self,
                     prompt: any,
                     output_schema: BaseModel,
                     input: dict[str, any]) -> any:
        """
        Invoke the configured model chain with structured output.

        Args:
            prompt: A prompt object or prompt string compatible with the langchain prompt operators used here.
            output_schema: A Pydantic `BaseModel` class describing the structured output schema.
            input: A dictionary of inputs to pass to the chain's `invoke` call.
        Returns:
            The raw result returned by the chain.
        Raises:
            Exception: Any unexpected exception raised while invoking the chain.
        """
        structured_llm = self.llm.with_structured_output(output_schema)
        chain = prompt | structured_llm

        try:
            result = chain.invoke(input)
            return result
        except Exception as e:
            return {
                "error": True,
                "error_message": str(e)
            }