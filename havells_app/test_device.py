"""Unit tests for the mock device module."""
import pytest
from device import SmartDevice, DeviceState, DEVICE_TOOLS


class TestSmartDevice:
    """Test cases for SmartDevice class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.device = SmartDevice()
    
    def test_initial_state(self):
        """Test device initializes with correct defaults."""
        assert self.device.power_state is False
        assert self.device.speed == 0
        assert self.device.brightness == 0
        assert self.device.connection_state == DeviceState.ONLINE
        assert len(self.device.operation_log) == 0
    
    def test_power_on(self):
        """Test power_on operation."""
        result = self.device.power_on()
        
        assert result["success"] is True
        assert "powered on" in result["message"].lower()
        assert self.device.power_state is True
        assert result["state"]["power"] is True
    
    def test_power_off(self):
        """Test power_off operation."""
        self.device.power_on()
        result = self.device.power_off()
        
        assert result["success"] is True
        assert "powered off" in result["message"].lower()
        assert self.device.power_state is False
        assert self.device.speed == 0
        assert self.device.brightness == 0
    
    def test_set_speed_valid(self):
        """Test setting valid fan speed."""
        self.device.power_on()
        result = self.device.set_speed(3)
        
        assert result["success"] is True
        assert self.device.speed == 3
        assert result["state"]["speed"] == 3
    
    def test_set_speed_invalid_range(self):
        """Test setting speed outside valid range."""
        self.device.power_on()
        
        # Test above max
        result = self.device.set_speed(6)
        assert result["success"] is False
        assert result["error"] == "invalid_parameter"
        
        # Test below min
        result = self.device.set_speed(-1)
        assert result["success"] is False
        assert result["error"] == "invalid_parameter"
    
    def test_set_speed_device_off(self):
        """Test setting speed when device is off."""
        result = self.device.set_speed(3)
        
        assert result["success"] is False
        assert result["error"] == "device_off"
    
    def test_set_brightness_valid(self):
        """Test setting valid brightness."""
        self.device.power_on()
        result = self.device.set_brightness(75)
        
        assert result["success"] is True
        assert self.device.brightness == 75
        assert result["state"]["brightness"] == 75
    
    def test_set_brightness_invalid_range(self):
        """Test setting brightness outside valid range."""
        self.device.power_on()
        
        # Test above max
        result = self.device.set_brightness(101)
        assert result["success"] is False
        assert result["error"] == "invalid_parameter"
        
        # Test below min
        result = self.device.set_brightness(-1)
        assert result["success"] is False
        assert result["error"] == "invalid_parameter"
    
    def test_set_brightness_device_off(self):
        """Test setting brightness when device is off."""
        result = self.device.set_brightness(50)
        
        assert result["success"] is False
        assert result["error"] == "device_off"
    
    def test_get_status(self):
        """Test getting device status."""
        self.device.power_on()
        self.device.set_speed(2)
        self.device.set_brightness(60)
        
        result = self.device.get_status()
        
        assert result["success"] is True
        assert result["state"]["power"] is True
        assert result["state"]["speed"] == 2
        assert result["state"]["brightness"] == 60
        assert result["state"]["connection"] == "online"
    
    def test_inject_failure_offline(self):
        """Test injecting offline failure."""
        self.device.inject_failure(DeviceState.OFFLINE, duration=2)
        
        # First operation should fail
        result1 = self.device.power_on()
        assert result1["success"] is False
        assert result1["error"] == "device_disconnected"
        
        # Second operation should fail
        result2 = self.device.power_on()
        assert result2["success"] is False
        assert result2["error"] == "device_disconnected"
        
        # Third operation should succeed (failure cleared)
        result3 = self.device.power_on()
        assert result3["success"] is True
    
    def test_inject_failure_timeout(self):
        """Test injecting timeout failure."""
        self.device.inject_failure(DeviceState.TIMEOUT, duration=1)
        
        result = self.device.power_on()
        assert result["success"] is False
        assert result["error"] == "connection_timeout"
    
    def test_clear_failure(self):
        """Test clearing injected failure."""
        self.device.inject_failure(DeviceState.OFFLINE, duration=5)
        self.device.clear_failure()
        
        result = self.device.power_on()
        assert result["success"] is True
    
    def test_operation_logging(self):
        """Test that operations are logged."""
        self.device.power_on()
        self.device.set_speed(3)
        
        log = self.device.get_operation_history()
        assert len(log) == 2
        assert log[0]["operation"] == "power_on"
        assert log[1]["operation"] == "set_speed"
        assert log[1]["params"]["speed"] == 3
    
    def test_reset(self):
        """Test device reset."""
        self.device.power_on()
        self.device.set_speed(3)
        self.device.inject_failure(DeviceState.OFFLINE, duration=2)
        
        self.device.reset()
        
        assert self.device.power_state is False
        assert self.device.speed == 0
        assert self.device.brightness == 0
        assert self.device.connection_state == DeviceState.ONLINE
        assert len(self.device.operation_log) == 0
        assert self.device._failure_mode is None
    
    def test_multiple_operations_sequence(self):
        """Test sequence of multiple operations."""
        # Turn on
        result = self.device.power_on()
        assert result["success"] is True
        
        # Set speed
        result = self.device.set_speed(4)
        assert result["success"] is True
        assert self.device.speed == 4
        
        # Set brightness
        result = self.device.set_brightness(80)
        assert result["success"] is True
        assert self.device.brightness == 80
        
        # Get status
        result = self.device.get_status()
        assert result["success"] is True
        assert result["state"]["power"] is True
        assert result["state"]["speed"] == 4
        assert result["state"]["brightness"] == 80
        
        # Turn off (should reset speed and brightness)
        result = self.device.power_off()
        assert result["success"] is True
        assert self.device.speed == 0
        assert self.device.brightness == 0


class TestDeviceTools:
    """Test device tool definitions."""
    
    def test_tool_definitions_exist(self):
        """Test that all tool definitions are present."""
        assert len(DEVICE_TOOLS) == 5
        
        tool_names = [tool["function"]["name"] for tool in DEVICE_TOOLS]
        assert "power_on" in tool_names
        assert "power_off" in tool_names
        assert "set_speed" in tool_names
        assert "set_brightness" in tool_names
        assert "get_status" in tool_names
    
    def test_tool_structure(self):
        """Test that tools have correct structure."""
        for tool in DEVICE_TOOLS:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
    
    def test_set_speed_parameters(self):
        """Test set_speed tool parameters."""
        tool = next(t for t in DEVICE_TOOLS if t["function"]["name"] == "set_speed")
        params = tool["function"]["parameters"]
        
        assert "speed" in params["properties"]
        assert params["properties"]["speed"]["type"] == "integer"
        assert params["properties"]["speed"]["minimum"] == 0
        assert params["properties"]["speed"]["maximum"] == 5
    
    def test_set_brightness_parameters(self):
        """Test set_brightness tool parameters."""
        tool = next(t for t in DEVICE_TOOLS if t["function"]["name"] == "set_brightness")
        params = tool["function"]["parameters"]
        
        assert "brightness" in params["properties"]
        assert params["properties"]["brightness"]["type"] == "integer"
        assert params["properties"]["brightness"]["minimum"] == 0
        assert params["properties"]["brightness"]["maximum"] == 100
