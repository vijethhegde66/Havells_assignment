"""Integration tests for the full agent system."""
import pytest
from device import SmartDevice, DeviceState
from agent import NaiveDeviceAgent
from reset_detector import ResetDetector


class TestAgentIntegration:
    """Integration tests for agent, device, and reset detector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.device = SmartDevice()
        self.agent = NaiveDeviceAgent(self.device)
        self.detector = ResetDetector()
    
    @pytest.mark.skip(reason="Requires Azure OpenAI API access")
    def test_clean_control_scenario(self):
        """Test scenario 1: Clean control with no failures."""
        # Process user request
        response = self.agent.process_turn("Turn on the fan and set speed to 3")
        
        # Verify device state
        assert self.device.power_state is True
        assert self.device.speed == 3
        
        # Verify no reset triggered
        agent_stats = self.agent.get_stats()
        recent_messages = self.agent.get_conversation_history()[-10:]
        should_reset, _ = self.detector.should_reset(
            agent_stats, recent_messages, response
        )
        assert should_reset is False
        
        # Verify tool calls happened
        assert agent_stats["tool_call_count"] >= 2
    
    @pytest.mark.skip(reason="Requires Azure OpenAI API access")
    def test_transient_failure_scenario(self):
        """Test scenario 2: Transient failure then recovery."""
        # Inject single failure
        self.device.inject_failure(DeviceState.OFFLINE, duration=1)
        
        # First attempt (will fail)
        response1 = self.agent.process_turn("Turn on the fan")
        assert "offline" in response1.lower() or "disconnect" in response1.lower()
        
        # Second attempt (should succeed)
        response2 = self.agent.process_turn("Please try turning on the fan again")
        
        # Eventually device should be on
        status = self.device.get_status()
        assert status["success"] is True
    
    @pytest.mark.skip(reason="Requires Azure OpenAI API access")
    def test_stale_failure_poisoning_scenario(self):
        """Test scenario 3: Stale-failure poisoning (core scenario)."""
        # Inject failure for first call only
        self.device.inject_failure(DeviceState.OFFLINE, duration=1)
        
        # Turn 1: Tool fails
        response1 = self.agent.process_turn("Turn on the fan")
        assert "offline" in response1.lower() or "disconnect" in response1.lower()
        
        # Turns 2-4: Agent should parrot error without calling tool
        for i in range(3):
            response = self.agent.process_turn("Can you turn on the fan?")
            
            # Check if reset should trigger
            agent_stats = self.agent.get_stats()
            recent_messages = self.agent.get_conversation_history()[-10:]
            should_reset, reason = self.detector.should_reset(
                agent_stats, recent_messages, response
            )
            
            if should_reset:
                # Reset triggered - test passed
                assert "stale" in reason or "tool_starvation" in reason
                return
        
        # If we get here, reset should have been triggered
        agent_stats = self.agent.get_stats()
        assert agent_stats["turns_since_last_tool_call"] >= 3
    
    def test_device_state_preserved_after_reset(self):
        """Test that device state is preserved when conversation resets."""
        # Turn on device and set state
        self.device.power_on()
        self.device.set_speed(4)
        self.device.set_brightness(80)
        
        # Reset conversation (not device)
        self.agent.reset_history()
        
        # Device state should be unchanged
        assert self.device.power_state is True
        assert self.device.speed == 4
        assert self.device.brightness == 80
        
        # But conversation history should be cleared
        messages = self.agent.get_conversation_history()
        assert len(messages) == 1  # Only system prompt
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        initial_stats = self.agent.get_stats()
        assert initial_stats["turn_count"] == 0
        assert initial_stats["tool_call_count"] == 0
        
        # Manually simulate a turn with tool call
        self.agent.turn_count = 1
        self.agent.tool_call_count = 1
        self.agent.last_tool_call_turn = 1
        
        stats = self.agent.get_stats()
        assert stats["turn_count"] == 1
        assert stats["tool_call_count"] == 1
        assert stats["turns_since_last_tool_call"] == 0
    
    def test_reset_detection_latency(self):
        """Test that reset detection meets latency budget."""
        # Create scenario that triggers multiple checks
        agent_stats = {
            "turn_count": 10,
            "tool_call_count": 5,
            "last_tool_call_turn": 5,
            "turns_since_last_tool_call": 5
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "Device offline"}
        ] * 5
        
        # Run detection multiple times
        for _ in range(50):
            self.detector.should_reset(agent_stats, messages, "Device offline")
        
        # Check latency stats
        stats = self.detector.get_stats()
        assert stats["within_budget"] is True
        assert stats["latency_stats"]["mean_ms"] < 100  # Should be much faster
        assert stats["latency_stats"]["max_ms"] < 500
    
    def test_operation_logging(self):
        """Test that operations are logged correctly."""
        # Perform operations
        self.device.power_on()
        self.device.set_speed(3)
        self.device.power_off()
        
        # Check log
        log = self.device.get_operation_history()
        assert len(log) == 3
        assert log[0]["operation"] == "power_on"
        assert log[1]["operation"] == "set_speed"
        assert log[2]["operation"] == "power_off"
        
        # Verify all have timestamps
        assert all("timestamp" in entry for entry in log)
    
    def test_failure_injection_reproducibility(self):
        """Test that failure injection is reproducible."""
        # Run 1
        device1 = SmartDevice()
        device1.inject_failure(DeviceState.OFFLINE, duration=3)
        
        results1 = []
        for _ in range(5):
            result = device1.power_on()
            results1.append(result["success"])
        
        # Run 2
        device2 = SmartDevice()
        device2.inject_failure(DeviceState.OFFLINE, duration=3)
        
        results2 = []
        for _ in range(5):
            result = device2.power_on()
            results2.append(result["success"])
        
        # Should be identical
        assert results1 == results2
        # First 3 should fail, last 2 should succeed
        assert results1 == [False, False, False, True, True]
    
    def test_multiple_reset_cycles(self):
        """Test multiple reset cycles."""
        for i in range(3):
            self.agent.turn_count = (i + 1) * 5
            self.detector.record_reset(turn=self.agent.turn_count)
            self.agent.reset_history()
        
        detector_stats = self.detector.get_stats()
        assert detector_stats["reset_count"] == 3
        assert detector_stats["last_reset_turn"] == 15
    
    def test_agent_message_history_growth(self):
        """Test that message history grows without reset."""
        initial_count = len(self.agent.get_conversation_history())
        
        # Manually add messages
        self.agent.messages.append({"role": "user", "content": "Test 1"})
        self.agent.messages.append({"role": "assistant", "content": "Response 1"})
        self.agent.messages.append({"role": "user", "content": "Test 2"})
        self.agent.messages.append({"role": "assistant", "content": "Response 2"})
        
        current_count = len(self.agent.get_conversation_history())
        assert current_count == initial_count + 4
        
        # After reset
        self.agent.reset_history()
        reset_count = len(self.agent.get_conversation_history())
        assert reset_count == 1  # Only system prompt


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_device_multiple_failure_types(self):
        """Test switching between failure types."""
        device = SmartDevice()
        
        # Inject offline failure
        device.inject_failure(DeviceState.OFFLINE, duration=1)
        result = device.power_on()
        assert result["error"] == "device_disconnected"
        
        # Inject timeout failure
        device.inject_failure(DeviceState.TIMEOUT, duration=1)
        result = device.power_on()
        assert result["error"] == "connection_timeout"
    
    def test_detector_empty_messages(self):
        """Test detector with empty message list."""
        detector = ResetDetector()
        agent_stats = {
            "turn_count": 0,
            "tool_call_count": 0,
            "last_tool_call_turn": 0,
            "turns_since_last_tool_call": 0
        }
        
        should_reset, reason = detector.should_reset(agent_stats, [], "")
        assert should_reset is False
    
    def test_agent_full_reset(self):
        """Test full reset including statistics."""
        device = SmartDevice()
        agent = NaiveDeviceAgent(device)
        
        # Set some state
        agent.turn_count = 10
        agent.tool_call_count = 5
        agent.messages = [{"role": "system", "content": "test"}] + [{}] * 20
        
        # Full reset
        agent.full_reset()
        
        assert agent.turn_count == 0
        assert agent.tool_call_count == 0
        assert len(agent.messages) == 1
    
    def test_device_invalid_operations(self):
        """Test device with invalid operation sequences."""
        device = SmartDevice()
        
        # Try to set speed without powering on
        result = device.set_speed(3)
        assert result["success"] is False
        
        # Try to set brightness without powering on
        result = device.set_brightness(50)
        assert result["success"] is False
        
        # Device state should still be off
        assert device.power_state is False
    
    def test_detector_with_tool_calls(self):
        """Test detector doesn't trigger on active tool usage."""
        detector = ResetDetector()
        
        # Agent is actively calling tools
        agent_stats = {
            "turn_count": 10,
            "tool_call_count": 10,
            "last_tool_call_turn": 10,
            "turns_since_last_tool_call": 0
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "Error occurred"}
        ] * 5
        
        should_reset, _ = detector.should_reset(
            agent_stats, messages, "Error occurred"
        )
        
        # Should not reset - tool calls are happening
        assert should_reset is False
