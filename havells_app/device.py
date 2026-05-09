"""Mock smart device with controllable failures for testing context poisoning."""
import time
import random
from typing import Dict, Any, Optional, Literal
from enum import Enum


class DeviceState(Enum):
    """Device connection states."""
    ONLINE = "online"
    OFFLINE = "offline"
    TIMEOUT = "timeout"


class SmartDevice:
    """
    Mock smart device (fan/light) with controllable failure injection.
    
    This device simulates a controllable appliance with operations that can
    fail deterministically for testing context poisoning scenarios.
    """
    
    def __init__(self):
        """Initialize device with default state."""
        self.power_state: bool = False
        self.speed: int = 0  # 0-5 for fan speed
        self.brightness: int = 0  # 0-100 for light brightness
        self.connection_state: DeviceState = DeviceState.ONLINE
        
        # Failure injection controls
        self._failure_mode: Optional[DeviceState] = None
        self._failure_count: int = 0
        self._failure_remaining: int = 0
        
        # Operation history for testing
        self.operation_log: list[Dict[str, Any]] = []
    
    def inject_failure(self, failure_type: DeviceState, duration: int = 1):
        """
        Inject a controllable failure for testing.
        
        Args:
            failure_type: Type of failure (OFFLINE or TIMEOUT)
            duration: Number of operations that should fail
        """
        if failure_type == DeviceState.ONLINE:
            raise ValueError("Cannot inject ONLINE as a failure")
        
        self._failure_mode = failure_type
        self._failure_remaining = duration
        self._failure_count = 0
    
    def clear_failure(self):
        """Clear any injected failures."""
        self._failure_mode = None
        self._failure_remaining = 0
        self._failure_count = 0
        self.connection_state = DeviceState.ONLINE
    
    def _check_failure(self) -> Optional[Dict[str, Any]]:
        """
        Check if operation should fail due to injected failure.
        
        Returns:
            Error response if failure should occur, None otherwise
        """
        if self._failure_mode and self._failure_remaining > 0:
            self._failure_count += 1
            self._failure_remaining -= 1
            
            if self._failure_mode == DeviceState.OFFLINE:
                self.connection_state = DeviceState.OFFLINE
                return {
                    "success": False,
                    "error": "device_disconnected",
                    "message": "Device is currently offline. Please check connection."
                }
            elif self._failure_mode == DeviceState.TIMEOUT:
                self.connection_state = DeviceState.TIMEOUT
                return {
                    "success": False,
                    "error": "connection_timeout",
                    "message": "Connection timeout. Device did not respond."
                }
        
        # If failure cleared, restore connection
        if self._failure_remaining == 0:
            self.connection_state = DeviceState.ONLINE
        
        return None
    
    def _log_operation(self, operation: str, params: Dict[str, Any], result: Dict[str, Any]):
        """Log operation for debugging and testing."""
        self.operation_log.append({
            "timestamp": time.time(),
            "operation": operation,
            "params": params,
            "result": result,
            "connection_state": self.connection_state.value
        })
    
    def power_on(self) -> Dict[str, Any]:
        """Turn on the device."""
        failure = self._check_failure()
        if failure:
            self._log_operation("power_on", {}, failure)
            return failure
        
        self.power_state = True
        result = {
            "success": True,
            "message": "Device powered on successfully.",
            "state": {
                "power": self.power_state,
                "speed": self.speed,
                "brightness": self.brightness
            }
        }
        self._log_operation("power_on", {}, result)
        return result
    
    def power_off(self) -> Dict[str, Any]:
        """Turn off the device."""
        failure = self._check_failure()
        if failure:
            self._log_operation("power_off", {}, failure)
            return failure
        
        self.power_state = False
        self.speed = 0
        self.brightness = 0
        result = {
            "success": True,
            "message": "Device powered off successfully.",
            "state": {
                "power": self.power_state,
                "speed": self.speed,
                "brightness": self.brightness
            }
        }
        self._log_operation("power_off", {}, result)
        return result
    
    def set_speed(self, speed: int) -> Dict[str, Any]:
        """
        Set fan speed (0-5).
        
        Args:
            speed: Speed level (0=off, 5=max)
        """
        failure = self._check_failure()
        if failure:
            self._log_operation("set_speed", {"speed": speed}, failure)
            return failure
        
        if not 0 <= speed <= 5:
            result = {
                "success": False,
                "error": "invalid_parameter",
                "message": f"Speed must be between 0 and 5. Got: {speed}"
            }
            self._log_operation("set_speed", {"speed": speed}, result)
            return result
        
        if not self.power_state and speed > 0:
            result = {
                "success": False,
                "error": "device_off",
                "message": "Device is off. Please turn it on first."
            }
            self._log_operation("set_speed", {"speed": speed}, result)
            return result
        
        self.speed = speed
        result = {
            "success": True,
            "message": f"Fan speed set to {speed}.",
            "state": {
                "power": self.power_state,
                "speed": self.speed,
                "brightness": self.brightness
            }
        }
        self._log_operation("set_speed", {"speed": speed}, result)
        return result
    
    def set_brightness(self, brightness: int) -> Dict[str, Any]:
        """
        Set light brightness (0-100).
        
        Args:
            brightness: Brightness level (0=off, 100=max)
        """
        failure = self._check_failure()
        if failure:
            self._log_operation("set_brightness", {"brightness": brightness}, failure)
            return failure
        
        if not 0 <= brightness <= 100:
            result = {
                "success": False,
                "error": "invalid_parameter",
                "message": f"Brightness must be between 0 and 100. Got: {brightness}"
            }
            self._log_operation("set_brightness", {"brightness": brightness}, result)
            return result
        
        if not self.power_state and brightness > 0:
            result = {
                "success": False,
                "error": "device_off",
                "message": "Device is off. Please turn it on first."
            }
            self._log_operation("set_brightness", {"brightness": brightness}, result)
            return result
        
        self.brightness = brightness
        result = {
            "success": True,
            "message": f"Brightness set to {brightness}%.",
            "state": {
                "power": self.power_state,
                "speed": self.speed,
                "brightness": self.brightness
            }
        }
        self._log_operation("set_brightness", {"brightness": brightness}, result)
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current device status."""
        failure = self._check_failure()
        if failure:
            self._log_operation("get_status", {}, failure)
            return failure
        
        result = {
            "success": True,
            "message": "Status retrieved successfully.",
            "state": {
                "power": self.power_state,
                "speed": self.speed,
                "brightness": self.brightness,
                "connection": self.connection_state.value
            }
        }
        self._log_operation("get_status", {}, result)
        return result
    
    def get_operation_history(self) -> list[Dict[str, Any]]:
        """Get operation log for debugging."""
        return self.operation_log.copy()
    
    def reset(self):
        """Reset device to initial state."""
        self.power_state = False
        self.speed = 0
        self.brightness = 0
        self.connection_state = DeviceState.ONLINE
        self.operation_log.clear()
        self.clear_failure()


# Tool definitions for the agent
DEVICE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "power_on",
            "description": "Turn on the smart device (fan or light).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "power_off",
            "description": "Turn off the smart device.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_speed",
            "description": "Set the fan speed level (0-5, where 0 is off and 5 is maximum).",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "integer",
                        "description": "Speed level from 0 to 5",
                        "minimum": 0,
                        "maximum": 5
                    }
                },
                "required": ["speed"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set the light brightness level (0-100, where 0 is off and 100 is maximum brightness).",
            "parameters": {
                "type": "object",
                "properties": {
                    "brightness": {
                        "type": "integer",
                        "description": "Brightness level from 0 to 100",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["brightness"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get the current status of the device including power state, speed, brightness, and connection status.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
