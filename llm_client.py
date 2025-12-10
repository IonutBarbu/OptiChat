"""
LLM Client abstraction layer for OptiChat.
Supports both OpenAI and AWS Bedrock via pydantic-ai.
"""

import os
from typing import Optional, List, Dict, Any, Union
from abc import ABC, abstractmethod
import json

# OpenAI imports
from openai import OpenAI, Client as OpenAIClient

# Pydantic-AI imports
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models.openai import OpenAIModel

try:
    from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
except ImportError:
    BedrockConverseModel = None
    BedrockModelSettings = None
    print("Warning: AWS Bedrock dependencies not available. Install pydantic-ai with bedrock support.")


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        seed: Optional[int] = None,
        response_format: Optional[Dict] = None,
        stream: bool = False,
        tools: Optional[List] = None,
        tool_choice: Optional[Union[str, Dict]] = None
    ) -> Union[str, Any]:
        """Generate a chat completion."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        pass


class OpenAILLMClient(LLMClient):
    """OpenAI implementation of LLM client."""
    
    def __init__(self, model_name: str = "gpt-4-turbo-preview", api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, **kwargs)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        seed: Optional[int] = None,
        response_format: Optional[Dict] = None,
        stream: bool = False,
        tools: Optional[List] = None,
        tool_choice: Optional[Union[str, Dict]] = None
    ) -> Union[str, Any]:
        """Generate a chat completion using OpenAI."""
        
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if seed is not None and self.model_name not in ["o3", "o1-preview", "o1-mini"]:
            kwargs["seed"] = seed
        
        if response_format:
            kwargs["response_format"] = response_format
        
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        
        completion = self.client.chat.completions.create(**kwargs)
        
        # Always return the completion object for non-streaming
        # This maintains compatibility with code expecting .choices[0].message.content
        return completion
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def get_raw_client(self):
        """Return the raw OpenAI client for backward compatibility."""
        return self.client


class BedrockLLMClient(LLMClient):
    """AWS Bedrock implementation using pydantic-ai's BedrockConverseModel."""
    
    # Map friendly names to Bedrock model IDs
    MODEL_ID_MAP = {
        "claude-sonnet-4": "eu.anthropic.claude-sonnet-4-20250514-v1:0",
        "gpt-oss-20b": "openai.gpt-oss-20b-1:0",
        "gpt-oss-120b": "openai.gpt-oss-120b-1:0",
    }
    
    def __init__(
        self, 
        model_name: str = "gpt-oss-120b", 
        max_tokens: int = 4096,
        **kwargs
    ):
        super().__init__(model_name, **kwargs)
        
        if BedrockConverseModel is None:
            raise ImportError(
                "BedrockConverseModel not available. Install pydantic-ai with bedrock support:\n"
                "pip install 'pydantic-ai[bedrock]'"
            )
        
        # Resolve model ID
        self.model_id = self.MODEL_ID_MAP.get(model_name, model_name)
        self.max_tokens = max_tokens
        
        # Create Bedrock model using pydantic-ai
        self.bedrock_model = BedrockConverseModel(self.model_id)
        
        # Create model settings
        self.model_settings = BedrockModelSettings(max_tokens=self.max_tokens)
    
    def _convert_messages_to_pydantic_format(self, messages: List[Dict[str, str]]) -> tuple:
        """Convert OpenAI-style messages to system prompt and message list."""
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt += content + "\n"
            else:
                user_messages.append({"role": role, "content": content})
        
        return system_prompt.strip(), user_messages
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        seed: Optional[int] = None,
        response_format: Optional[Dict] = None,
        stream: bool = False,
        tools: Optional[List] = None,
        tool_choice: Optional[Union[str, Dict]] = None
    ) -> Union[str, Any]:
        """Generate a chat completion using AWS Bedrock via pydantic-ai."""
        
        system_prompt, user_messages = self._convert_messages_to_pydantic_format(messages)
        
        # Create a pydantic-ai agent with Bedrock model
        agent = PydanticAgent(
            model=self.bedrock_model,
            model_settings=self.model_settings,
            system_prompt=system_prompt if system_prompt else "You are a helpful assistant."
        )
        
        # Build the user prompt from messages
        if user_messages:
            user_prompt = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in user_messages
            ])
        else:
            user_prompt = messages[-1]["content"] if messages else ""
        
        # Handle JSON mode
        if response_format and response_format.get("type") == "json_object":
            user_prompt += "\n\nPlease respond with valid JSON only."
        
        try:
            # Run the agent synchronously
            import asyncio
            
            # Check if we're in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context - use ThreadPoolExecutor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, agent.run(user_prompt))
                    result = future.result()
            except RuntimeError:
                # No event loop running
                result = asyncio.run(agent.run(user_prompt))
            
            # Handle tool calls if present
            if tools and hasattr(result, 'all_messages'):
                # Check if any message has tool calls
                for msg in result.all_messages():
                    if hasattr(msg, 'parts'):
                        for part in msg.parts:
                            if hasattr(part, 'tool_name'):
                                # Return format similar to OpenAI
                                class MockToolCall:
                                    def __init__(self, tool_name, tool_args):
                                        self.function = type('obj', (object,), {
                                            'name': tool_name,
                                            'arguments': json.dumps(tool_args)
                                        })()
                                
                                class MockCompletion:
                                    def __init__(self, result, tool_calls):
                                        self.choices = [type('obj', (object,), {
                                            'message': type('obj', (object,), {
                                                'content': str(result.output),
                                                'tool_calls': tool_calls
                                            })()
                                        })()]
                                
                                tool_calls = [MockToolCall(part.tool_name, part.args)]
                                return MockCompletion(result, tool_calls)
            
            if stream:
                # For streaming, return the data wrapped in a generator
                def stream_generator():
                    yield str(result.output)
                return stream_generator()
            else:
                return str(result.output)
        
        except Exception as e:
            print(f"Error calling Bedrock model: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"Error: {str(e)}"
            
            # Return appropriate type based on stream parameter
            if stream:
                def error_generator():
                    yield error_msg
                return error_generator()
            else:
                return error_msg
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def get_model_id(self) -> str:
        return self.model_id


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    @staticmethod
    def create_client(
        provider: str = "openai",
        model_name: Optional[str] = None,
        **kwargs
    ) -> LLMClient:
        """
        Create an LLM client.
        
        Args:
            provider: "openai" or "bedrock"
            model_name: Model name (provider-specific)
            **kwargs: Additional provider-specific arguments
        
        Returns:
            LLMClient instance
        """
        provider = provider.lower()
        
        if provider == "openai":
            default_model = "gpt-4-turbo-preview"
            return OpenAILLMClient(
                model_name=model_name or default_model,
                **kwargs
            )
        
        elif provider == "bedrock":
            default_model = "gpt-oss-120b"
            return BedrockLLMClient(
                model_name=model_name or default_model,
                **kwargs
            )
        
        else:
            raise ValueError(f"Unknown provider: {provider}. Choose 'openai' or 'bedrock'")
    
    @staticmethod
    def get_available_models(provider: str) -> List[str]:
        """Get list of available models for a provider."""
        if provider.lower() == "openai":
            return [
                "gpt-4-turbo-preview",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-4-1106-preview",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "o1-preview",
                "o1-mini"
            ]
        elif provider.lower() == "bedrock":
            return list(BedrockLLMClient.MODEL_ID_MAP.keys())
        else:
            return []


# Mock classes for backward compatibility
class MockMessage:
    """Mock OpenAI message object."""
    def __init__(self, content: str, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

class MockChoice:
    """Mock OpenAI choice object."""
    def __init__(self, message: MockMessage):
        self.message = message

class MockCompletion:
    """Mock OpenAI completion object."""
    def __init__(self, choices: List[MockChoice]):
        self.choices = choices


# Backward compatibility wrapper
class UnifiedLLMClient:
    """
    Unified client that works with both OpenAI and Bedrock,
    maintaining backward compatibility with OpenAI client interface.
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.chat = self
        self.completions = self
    
    def create(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        temperature: float = 0.1,
        seed: Optional[int] = None,
        response_format: Optional[Dict] = None,
        stream: bool = False,
        tools: Optional[List] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        **kwargs
    ):
        """Create a chat completion (mimics OpenAI interface)."""
        result = self.llm_client.chat_completion(
            messages=messages,
            temperature=temperature,
            seed=seed,
            response_format=response_format,
            stream=stream,
            tools=tools,
            tool_choice=tool_choice
        )
        
        # If streaming, return as-is
        if stream:
            return result
        
        # If result is already a completion object (e.g., from OpenAI with tool calls), return it
        if hasattr(result, 'choices'):
            return result
        
        # If result is a string, wrap it in a mock completion object
        if isinstance(result, str):
            message = MockMessage(content=result)
            choice = MockChoice(message=message)
            return MockCompletion(choices=[choice])
        
        # Otherwise return as-is
        return result
    
    def get_model_name(self) -> str:
        return self.llm_client.get_model_name()
