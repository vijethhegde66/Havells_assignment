"""Reset detection mechanism for identifying and handling context poisoning."""
import time
import re
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

from config import Config


class ResetDetector:
    """
    Detects context poisoning and triggers session history reset.
    
    This detector uses fast, latency-optimized heuristics to identify:
    1. Stale error parroting (agent repeats errors without re-invoking tools)
    2. Tool call starvation (many turns without tool invocation)
    3. Response repetition (near-identical responses)
    
    Design philosophy:
    - Use cheap string operations and counters (no LLM calls, no embeddings)
    - Target <500ms latency per turn
    - Optimize for the stale-failure pattern (the core assignment scenario)
    - Accept some false negatives to avoid false positives
    """
    
    def __init__(self):
        """Initialize the reset detector."""
        # Thresholds (tuned for the assignment scenarios)
        self.TOOL_STARVATION_THRESHOLD = 3  # Reset if no tool call in N turns
        self.ERROR_REPETITION_THRESHOLD = 2  # Reset if same error appears N times
        self.RESPONSE_SIMILARITY_THRESHOLD = 0.85  # Jaccard similarity for repetition
        
        # Known error patterns (from device module)
        self.ERROR_PATTERNS = [
            "device disconnected",
            "device is currently offline",
            "connection timeout",
            "device did not respond",
            "still disconnected",
            "still offline"
        ]
        
        # State tracking
        self.reset_count = 0
        self.last_reset_turn = 0
        self.detection_latencies: List[float] = []
    
    def should_reset(
        self,
        agent_stats: Dict[str, Any],
        recent_messages: List[Dict[str, Any]],
        last_response: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if context should be reset.
        
        Args:
            agent_stats: Statistics from the agent (turn count, tool calls, etc.)
            recent_messages: Recent conversation messages (last 5-10 turns)
            last_response: The agent's most recent response
            
        Returns:
            Tuple of (should_reset, reason)
        """
        start_time = time.time()
        
        # Signal 1: Tool call starvation
        # If the agent hasn't called a tool in N turns despite device-related conversation
        turns_since_tool = agent_stats.get("turns_since_last_tool_call", 0)
        if turns_since_tool >= self.TOOL_STARVATION_THRESHOLD:
            # Check if recent messages contain device-related requests
            if self._contains_device_request(recent_messages[-3:]):
                latency = (time.time() - start_time) * 1000
                self.detection_latencies.append(latency)
                return True, f"tool_starvation (no tool call in {turns_since_tool} turns)"
        
        # Signal 2: Error message repetition (stale-failure parroting)
        # If the same error appears multiple times in recent responses
        error_counts = self._count_error_repetitions(recent_messages)
        for error_pattern, count in error_counts.items():
            if count >= self.ERROR_REPETITION_THRESHOLD:
                # Verify no recent tool calls (confirms it's stale, not genuine failures)
                if turns_since_tool >= 1:
                    latency = (time.time() - start_time) * 1000
                    self.detection_latencies.append(latency)
                    return True, f"stale_error_parroting ('{error_pattern}' repeated {count}x)"
        
        # Signal 3: Response similarity (near-identical responses)
        # If last 2-3 responses are very similar, likely stuck in a loop
        # But only if tool calls aren't happening (avoid false positives on genuine repeated errors)
        if len(recent_messages) >= 4 and turns_since_tool >= 1:
            assistant_responses = [
                msg["content"] for msg in recent_messages[-4:]
                if msg["role"] == "assistant" and msg.get("content")
            ]
            if len(assistant_responses) >= 2:
                similarity = self._calculate_similarity(
                    assistant_responses[-1],
                    assistant_responses[-2]
                )
                if similarity > self.RESPONSE_SIMILARITY_THRESHOLD:
                    latency = (time.time() - start_time) * 1000
                    self.detection_latencies.append(latency)
                    return True, f"response_repetition (similarity={similarity:.2f})"
        
        latency = (time.time() - start_time) * 1000
        self.detection_latencies.append(latency)
        return False, None
    
    def _contains_device_request(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Check if messages contain device control requests.
        
        Uses simple keyword matching for speed.
        """
        device_keywords = [
            "turn on", "turn off", "power", "switch",
            "set speed", "speed", "fan",
            "brightness", "light", "dim",
            "status", "check"
        ]
        
        for msg in messages:
            if msg["role"] == "user":
                content = msg.get("content", "").lower()
                if any(keyword in content for keyword in device_keywords):
                    return True
        
        return False
    
    def _count_error_repetitions(self, messages: List[Dict[str, Any]]) -> Counter:
        """
        Count how many times each error pattern appears in recent messages.
        
        Fast pattern matching using simple string search.
        """
        error_counts = Counter()
        
        # Look at last 5 assistant messages
        assistant_messages = [
            msg.get("content", "") for msg in messages[-10:]
            if msg["role"] == "assistant" and msg.get("content")
        ]
        
        for response in assistant_messages:
            response_lower = response.lower()
            for pattern in self.ERROR_PATTERNS:
                if pattern in response_lower:
                    error_counts[pattern] += 1
        
        return error_counts
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate Jaccard similarity between two texts.
        
        Fast word-level similarity using set operations.
        Much faster than edit distance or embeddings.
        """
        if not text1 or not text2:
            return 0.0
        
        # Tokenize into words (simple split)
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def record_reset(self, turn: int):
        """Record that a reset occurred."""
        self.reset_count += 1
        self.last_reset_turn = turn
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics including latency metrics."""
        latencies = self.detection_latencies
        
        return {
            "reset_count": self.reset_count,
            "last_reset_turn": self.last_reset_turn,
            "detection_calls": len(latencies),
            "latency_stats": {
                "mean_ms": sum(latencies) / len(latencies) if latencies else 0,
                "max_ms": max(latencies) if latencies else 0,
                "min_ms": min(latencies) if latencies else 0,
                "p95_ms": self._percentile(latencies, 0.95) if latencies else 0,
                "p99_ms": self._percentile(latencies, 0.99) if latencies else 0,
            },
            "within_budget": all(l < Config.RESET_LATENCY_BUDGET_MS for l in latencies)
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a list."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def reset_stats(self):
        """Reset statistics (for testing)."""
        self.reset_count = 0
        self.last_reset_turn = 0
        self.detection_latencies.clear()
