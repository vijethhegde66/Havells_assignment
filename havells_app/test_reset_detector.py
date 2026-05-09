"""Unit tests for the reset detector module."""
import pytest
from reset_detector import ResetDetector


class TestResetDetector:
    """Test cases for ResetDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ResetDetector()
    
    def test_initial_state(self):
        """Test detector initializes with correct defaults."""
        assert self.detector.reset_count == 0
        assert self.detector.last_reset_turn == 0
        assert len(self.detector.detection_latencies) == 0
    
    def test_no_reset_on_clean_operation(self):
        """Test no reset triggered for normal operation."""
        agent_stats = {
            "turn_count": 1,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 0
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "I've turned on the fan successfully."}
        ]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats, messages, "I've turned on the fan successfully."
        )
        
        assert should_reset is False
        assert reason is None
    
    def test_tool_starvation_detection(self):
        """Test detection of tool call starvation."""
        agent_stats = {
            "turn_count": 4,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 3
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "The device is offline"},
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "The device is still offline"}
        ]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats, messages, "The device is still offline"
        )
        
        assert should_reset is True
        assert "tool_starvation" in reason
    
    def test_tool_starvation_not_triggered_without_device_keywords(self):
        """Test tool starvation not triggered for non-device conversation."""
        agent_stats = {
            "turn_count": 4,
            "tool_call_count": 0,
            "last_tool_call_turn": 0,
            "turns_since_last_tool_call": 4
        }
        
        messages = [
            {"role": "user", "content": "Tell me a joke"},
            {"role": "assistant", "content": "Why did the chicken cross the road?"},
            {"role": "user", "content": "Why?"},
            {"role": "assistant", "content": "To get to the other side!"}
        ]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats, messages, "To get to the other side!"
        )
        
        assert should_reset is False
    
    def test_error_repetition_detection(self):
        """Test detection of repeated error messages."""
        agent_stats = {
            "turn_count": 3,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 2
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "The device is currently offline. Please check connection."},
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "The device is currently offline. Please check connection."}
        ]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats, messages, "The device is currently offline. Please check connection."
        )
        
        assert should_reset is True
        assert "stale_error_parroting" in reason
    
    def test_error_repetition_not_triggered_with_tool_calls(self):
        """Test error repetition not triggered if tool calls are happening."""
        agent_stats = {
            "turn_count": 3,
            "tool_call_count": 3,
            "last_tool_call_turn": 3,
            "turns_since_last_tool_call": 0
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "The device is currently offline."},
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "The device is currently offline."}
        ]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats, messages, "The device is currently offline."
        )
        
        # Should not reset if tool calls are happening (genuine failures)
        assert should_reset is False
    
    def test_response_similarity_detection(self):
        """Test detection of highly similar responses."""
        agent_stats = {
            "turn_count": 3,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 2
        }
        
        # Very similar responses
        response1 = "I apologize but the device appears to be disconnected right now"
        response2 = "I apologize but the device appears to be disconnected right now"
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": response1},
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": response2}
        ]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats, messages, response2
        )
        
        assert should_reset is True
        assert "response_repetition" in reason
    
    def test_contains_device_request(self):
        """Test device request detection."""
        # Should detect device keywords
        messages_with_device = [
            {"role": "user", "content": "Turn on the fan"}
        ]
        assert self.detector._contains_device_request(messages_with_device) is True
        
        messages_with_light = [
            {"role": "user", "content": "Set brightness to 50"}
        ]
        assert self.detector._contains_device_request(messages_with_light) is True
        
        # Should not detect non-device requests
        messages_without_device = [
            {"role": "user", "content": "Tell me a joke"}
        ]
        assert self.detector._contains_device_request(messages_without_device) is False
    
    def test_count_error_repetitions(self):
        """Test error counting logic."""
        messages = [
            {"role": "assistant", "content": "The device is currently offline."},
            {"role": "assistant", "content": "The device is currently offline."},
            {"role": "assistant", "content": "Connection timeout occurred."}
        ]
        
        counts = self.detector._count_error_repetitions(messages)
        
        assert counts["device is currently offline"] == 2
        assert counts["connection timeout"] == 1
    
    def test_calculate_similarity(self):
        """Test Jaccard similarity calculation."""
        # Identical strings
        text1 = "Turn on the fan"
        text2 = "Turn on the fan"
        similarity = self.detector._calculate_similarity(text1, text2)
        assert similarity == 1.0
        
        # Completely different
        text1 = "Turn on the fan"
        text2 = "Hello world"
        similarity = self.detector._calculate_similarity(text1, text2)
        assert similarity < 0.3
        
        # Partially similar
        text1 = "Turn on the fan please"
        text2 = "Turn off the fan"
        similarity = self.detector._calculate_similarity(text1, text2)
        assert 0.4 < similarity < 0.8
        
        # Empty strings
        similarity = self.detector._calculate_similarity("", "test")
        assert similarity == 0.0
    
    def test_record_reset(self):
        """Test reset recording."""
        self.detector.record_reset(turn=5)
        
        assert self.detector.reset_count == 1
        assert self.detector.last_reset_turn == 5
        
        self.detector.record_reset(turn=10)
        assert self.detector.reset_count == 2
        assert self.detector.last_reset_turn == 10
    
    def test_latency_tracking(self):
        """Test that latency is tracked for each detection call."""
        agent_stats = {
            "turn_count": 1,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 0
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "Done"}
        ]
        
        # Make several detection calls
        for _ in range(5):
            self.detector.should_reset(agent_stats, messages, "Done")
        
        assert len(self.detector.detection_latencies) == 5
        assert all(latency >= 0 for latency in self.detector.detection_latencies)
    
    def test_latency_budget(self):
        """Test that detection stays within latency budget."""
        agent_stats = {
            "turn_count": 5,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 4
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "Device offline"},
        ] * 5
        
        # Run detection
        self.detector.should_reset(agent_stats, messages, "Device offline")
        
        stats = self.detector.get_stats()
        
        # All latencies should be under 500ms
        assert stats["within_budget"] is True
        assert stats["latency_stats"]["max_ms"] < 500
        assert stats["latency_stats"]["mean_ms"] < 500
    
    def test_get_stats(self):
        """Test statistics reporting."""
        self.detector.record_reset(turn=3)
        self.detector.record_reset(turn=7)
        
        # Make some detection calls to generate latency data
        agent_stats = {"turn_count": 1, "tool_call_count": 1, 
                      "last_tool_call_turn": 1, "turns_since_last_tool_call": 0}
        messages = [{"role": "user", "content": "test"}]
        
        for _ in range(10):
            self.detector.should_reset(agent_stats, messages, "test")
        
        stats = self.detector.get_stats()
        
        assert stats["reset_count"] == 2
        assert stats["last_reset_turn"] == 7
        assert stats["detection_calls"] == 10
        assert "latency_stats" in stats
        assert "mean_ms" in stats["latency_stats"]
        assert "max_ms" in stats["latency_stats"]
        assert "p95_ms" in stats["latency_stats"]
        assert "p99_ms" in stats["latency_stats"]
    
    def test_reset_stats(self):
        """Test statistics reset."""
        self.detector.record_reset(turn=5)
        self.detector.detection_latencies.append(10.0)
        
        self.detector.reset_stats()
        
        assert self.detector.reset_count == 0
        assert self.detector.last_reset_turn == 0
        assert len(self.detector.detection_latencies) == 0
    
    def test_percentile_calculation(self):
        """Test percentile calculation."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        p50 = self.detector._percentile(data, 0.5)
        assert 5.0 <= p50 <= 6.0
        
        p95 = self.detector._percentile(data, 0.95)
        assert 9.0 <= p95 <= 10.0
        
        p99 = self.detector._percentile(data, 0.99)
        assert p99 == 10.0
        
        # Empty list
        assert self.detector._percentile([], 0.95) == 0.0
    
    def test_threshold_values(self):
        """Test that threshold constants are reasonable."""
        assert self.detector.TOOL_STARVATION_THRESHOLD >= 2
        assert self.detector.ERROR_REPETITION_THRESHOLD >= 1
        assert 0.7 <= self.detector.RESPONSE_SIMILARITY_THRESHOLD <= 0.95
    
    def test_multiple_signals_priority(self):
        """Test that multiple signals can trigger independently."""
        # Tool starvation should trigger even without error repetition
        agent_stats = {
            "turn_count": 5,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 4
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "Working on it..."}
        ]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats, messages, "Working on it..."
        )
        
        assert should_reset is True
        assert "tool_starvation" in reason
