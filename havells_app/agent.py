"""Deliberately naive agent for device control with context poisoning susceptibility."""
import json
from typing import Dict, Any, List, Optional
from openai import AzureOpenAI
from azure.identity import ClientSecretCredential, get_bearer_token_provider

from config import Config
from device import SmartDevice, DEVICE_TOOLS


class NaiveDeviceAgent:
    """
    A deliberately naive agent that controls smart devices.
    
    This agent is designed to exhibit context poisoning vulnerabilities:
    - Does NOT have prompt instructions to retry failed tools
    - Does NOT filter or detect stale errors in conversation history
    - Will naturally parrot previous error messages without re-invoking tools
    - Accumulates all conversation history without selective truncation
    
    The naive design is intentional - the reset mechanism should handle poisoning.
    """
    
    # Simple system prompt with NO prevention mechanisms
    SYSTEM_PROMPT = """You are a helpful assistant that controls smart home devices like fans and lights.
When the user asks you to control a device, use the available tools to perform the action.
Respond naturally and helpfully to the user."""
    
    def __init__(self, device: SmartDevice):
        """
        Initialize the naive agent.
        
        Args:
            device: The smart device to control
        """
        self.device = device
        
        # Use Azure AD authentication (same as working codebase)
        scope = "https://cognitiveservices.azure.com/.default"
        credential = ClientSecretCredential(
            tenant_id=Config.TECHDEMO_TENANT_ID,
            client_id=Config.TECHDEMO_CLIENT_ID,
            client_secret=Config.TECHDEMO_CLIENT_SECRET
        )
        token_provider = get_bearer_token_provider(credential, scope)
        
        self.client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            api_version=Config.OPENAI_API_VERSION,
            azure_ad_token_provider=token_provider
        )
        
        # Conversation history - intentionally accumulates everything
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        
        # Statistics
        self.turn_count = 0
        self.tool_call_count = 0
        self.last_tool_call_turn = 0
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a device tool.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        # Map tool names to device methods
        tool_map = {
            "power_on": self.device.power_on,
            "power_off": self.device.power_off,
            "set_speed": self.device.set_speed,
            "set_brightness": self.device.set_brightness,
            "get_status": self.device.get_status
        }
        
        if tool_name not in tool_map:
            return {
                "success": False,
                "error": "unknown_tool",
                "message": f"Unknown tool: {tool_name}"
            }
        
        self.tool_call_count += 1
        self.last_tool_call_turn = self.turn_count
        
        # Execute the tool
        try:
            method = tool_map[tool_name]
            result = method(**arguments)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": "execution_error",
                "message": f"Error executing {tool_name}: {str(e)}"
            }
    
    def process_turn(self, user_message: str) -> str:
        """
        Process a single conversation turn.
        
        Args:
            user_message: User's input message
            
        Returns:
            Agent's response
        """
        self.turn_count += 1
        
        # Add user message to history (naive - no filtering)
        self.messages.append({"role": "user", "content": user_message})
        
        # Call LLM with tools
        response = self.client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=self.messages,
            tools=DEVICE_TOOLS,
            tool_choice="auto",
            temperature=Config.LLM_TEMPERATURE,
            max_tokens=Config.LLM_MAX_TOKENS
        )
        
        assistant_message = response.choices[0].message
        
        # Handle tool calls
        if assistant_message.tool_calls:
            # Add assistant message with tool calls to history
            self.messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                # Execute tool
                result = self._execute_tool(tool_name, arguments)
                
                # Add tool result to history (naive - adds ALL results including errors)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
            
            # Get final response after tool execution
            final_response = self.client.chat.completions.create(
                model=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=self.messages,
                temperature=Config.LLM_TEMPERATURE,
                max_tokens=Config.LLM_MAX_TOKENS
            )
            
            final_message = final_response.choices[0].message
            self.messages.append({
                "role": "assistant",
                "content": final_message.content
            })
            
            return final_message.content
        else:
            # No tool calls - just add response to history
            self.messages.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            
            return assistant_message.content
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the current conversation history."""
        return self.messages.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "turn_count": self.turn_count,
            "tool_call_count": self.tool_call_count,
            "last_tool_call_turn": self.last_tool_call_turn,
            "turns_since_last_tool_call": self.turn_count - self.last_tool_call_turn,
            "message_count": len(self.messages)
        }
    
    def reset_history(self):
        """
        Reset conversation history.
        
        This is called by the reset mechanism when context poisoning is detected.
        """
        # Keep only the system prompt
        self.messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        
        # Note: We do NOT reset turn_count or other stats
        # This allows the reset detector to track reset frequency
    
    def full_reset(self):
        """Full reset including statistics."""
        self.reset_history()
        self.turn_count = 0
        self.tool_call_count = 0
        self.last_tool_call_turn = 0
