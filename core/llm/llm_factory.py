from langchain_google_genai import ChatGoogleGenerativeAI
from shared.singleton_meta_class import SingletonMetaClass

class LLMFactory(metaclass=SingletonMetaClass):
    """
    Factory for creating Google Gemini instances with simplified access.
    Uses SingletonMetaClass for singleton pattern implementation.
    """

    GEMINI_FLASH_MODEL_NAME = "gemini-2.0-flash"
    
    _default_configs = {
        GEMINI_FLASH_MODEL_NAME: {
            "model": GEMINI_FLASH_MODEL_NAME,
            "temperature": 0.2,
            "disable_streaming": True,
        }
    }
    
    @classmethod
    def create_gemini_flash(cls, **kwargs) -> ChatGoogleGenerativeAI:
        """
        Creates a Gemini Flash instance with the specified parameters.
        
        Args:
            **kwargs: Additional configuration parameters that override defaults
            
        Returns:
            ChatGoogleGenerativeAI: A new instance with the specified parameters
        """
        return cls.create_llm(cls.GEMINI_FLASH_MODEL_NAME, **kwargs)
    
    @classmethod
    def create_llm(cls, model_name: str, **kwargs) -> ChatGoogleGenerativeAI:
        """
        Creates an LLM instance with the specified parameters.
        
        Args:
            model_name: Name of the model
            **kwargs: Additional configuration parameters
            
        Returns:
            ChatGoogleGenerativeAI: A new instance
        """
        config = cls._default_configs.get(model_name, {}).copy()
        config.update(kwargs)
        return ChatGoogleGenerativeAI(**config)