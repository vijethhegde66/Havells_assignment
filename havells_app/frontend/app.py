"""Streamlit frontend for Smart Device Control Agent."""
import streamlit as st
import requests
import uuid
from typing import Optional

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Smart Device Control",
    page_icon="🏠",
    layout="wide"
)

def init_session():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        response = requests.post(f"{API_BASE_URL}/session/create", 
                                params={"session_id": st.session_state.session_id})
        if response.status_code != 200:
            st.error("Failed to create session")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "reset_count" not in st.session_state:
        st.session_state.reset_count = 0


def send_message(message: str):
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "session_id": st.session_state.session_id,
                "message": message
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data["reset_triggered"]:
                st.session_state.reset_count += 1
                st.toast(f"🔄 Reset triggered: {data['reset_reason']}", icon="⚠️")
            
            return data
        else:
            st.error(f"Error: {response.text}")
            return None
    
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None


def get_stats():
    try:
        response = requests.get(
            f"{API_BASE_URL}/session/{st.session_state.session_id}/stats"
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def inject_failure(failure_type: str, duration: int):
    try:
        response = requests.post(
            f"{API_BASE_URL}/session/{st.session_state.session_id}/device/inject-failure",
            json={
                "failure_type": failure_type,
                "duration": duration
            }
        )
        if response.status_code == 200:
            st.success(f"Injected {failure_type} failure for {duration} operations")
        else:
            st.error("Failed to inject failure")
    except Exception as e:
        st.error(f"Error: {str(e)}")


def clear_failure():
    try:
        response = requests.post(
            f"{API_BASE_URL}/session/{st.session_state.session_id}/device/clear-failure"
        )
        if response.status_code == 200:
            st.success("Device failures cleared")
    except Exception as e:
        st.error(f"Error: {str(e)}")


def reset_conversation():
    try:
        response = requests.post(
            f"{API_BASE_URL}/session/{st.session_state.session_id}/reset"
        )
        if response.status_code == 200:
            st.session_state.messages = []
            st.success("Conversation reset")
            st.rerun()
    except Exception as e:
        st.error(f"Error: {str(e)}")


init_session()

st.title("🏠 Smart Device Control Agent")
st.markdown("Control your smart fan and light with natural language")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat")
    
    chat_container = st.container(height=400)
    
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    
    if prompt := st.chat_input("Type your message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        with st.spinner("Thinking..."):
            result = send_message(prompt)
        
        if result:
            response = result["response"]
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(response)
            
            st.rerun()

with col2:
    st.subheader("📊 Statistics")
    
    stats = get_stats()
    
    if stats:
        agent_stats = stats["agent_stats"]
        detector_stats = stats["detector_stats"]
        device_status = stats["device_status"]
        
        st.metric("Turns", agent_stats["turn_count"])
        st.metric("Tool Calls", agent_stats["tool_call_count"])
        st.metric("Resets", detector_stats["reset_count"])
        
        with st.expander("🔧 Device Status"):
            if device_status["success"]:
                state = device_status["state"]
                st.write(f"**Power:** {'ON' if state['power'] else 'OFF'}")
                st.write(f"**Fan Speed:** {state['speed']}/5")
                st.write(f"**Brightness:** {state['brightness']}%")
                st.write(f"**Connection:** {state['connection']}")
            else:
                st.error(device_status["message"])
        
        with st.expander("⚡ Latency Metrics"):
            latency = detector_stats["latency_stats"]
            st.write(f"**Mean:** {latency['mean_ms']:.2f} ms")
            st.write(f"**Max:** {latency['max_ms']:.2f} ms")
            st.write(f"**P95:** {latency['p95_ms']:.2f} ms")
            st.write(f"**Within Budget:** {'✓' if detector_stats['within_budget'] else '✗'}")
    
    st.divider()
    
    st.subheader("🧪 Testing Controls")
    
    with st.expander("Inject Failure"):
        failure_type = st.selectbox("Failure Type", ["offline", "timeout"])
        duration = st.number_input("Duration (operations)", min_value=1, max_value=10, value=1)
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Inject", use_container_width=True):
                inject_failure(failure_type, duration)
        with col_b:
            if st.button("Clear", use_container_width=True):
                clear_failure()
    
    if st.button("🔄 Reset Conversation", use_container_width=True):
        reset_conversation()
    
    st.divider()
    
    st.subheader("💡 Quick Commands")
    st.markdown("""
    - "Turn on the fan"
    - "Set fan speed to 3"
    - "Turn on the light"
    - "Set brightness to 50%"
    - "Get device status"
    """)

st.sidebar.title("ℹ️ About")
st.sidebar.markdown("""
This application demonstrates an LLM-based agent with automatic context poisoning detection and reset.

**Features:**
- Natural language device control
- Automatic stale-error detection
- Session history reset
- Latency monitoring
- Failure injection for testing
""")

st.sidebar.divider()
st.sidebar.caption(f"Session ID: {st.session_state.session_id[:8]}...")
