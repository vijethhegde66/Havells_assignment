"""FastAPI backend for the Smart Device Control Agent."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from device import SmartDevice, DeviceState
from agent import NaiveDeviceAgent
from reset_detector import ResetDetector

app = FastAPI(title="Smart Device Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: Dict[str, Dict[str, Any]] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    reset_triggered: bool
    reset_reason: Optional[str]
    stats: Dict[str, Any]


class SessionResponse(BaseModel):
    session_id: str
    message: str


class StatsResponse(BaseModel):
    agent_stats: Dict[str, Any]
    detector_stats: Dict[str, Any]
    device_status: Dict[str, Any]


class FailureRequest(BaseModel):
    failure_type: str
    duration: int


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        device = SmartDevice()
        agent = NaiveDeviceAgent(device)
        detector = ResetDetector()
        
        sessions[session_id] = {
            "device": device,
            "agent": agent,
            "detector": detector,
            "conversation_log": []
        }
    
    return sessions[session_id]


@app.get("/")
async def root():
    return {"status": "ok", "message": "Smart Device Control API"}


@app.post("/session/create", response_model=SessionResponse)
async def create_session(session_id: Optional[str] = None):
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
    
    get_or_create_session(session_id)
    return SessionResponse(
        session_id=session_id,
        message="Session created successfully"
    )


@app.post("/session/{session_id}/reset", response_model=SessionResponse)
async def reset_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    session["agent"].reset_history()
    session["conversation_log"].clear()
    
    return SessionResponse(
        session_id=session_id,
        message="Session reset successfully"
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    return {"message": "Session deleted successfully"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session = get_or_create_session(request.session_id)
    
    agent = session["agent"]
    detector = session["detector"]
    
    try:
        response = agent.process_turn(request.message)
        
        session["conversation_log"].append({
            "turn": agent.turn_count,
            "user": request.message,
            "assistant": response
        })
        
        agent_stats = agent.get_stats()
        recent_messages = agent.get_conversation_history()[-10:]
        
        should_reset, reason = detector.should_reset(
            agent_stats,
            recent_messages,
            response
        )
        
        reset_triggered = False
        reset_reason = None
        
        if should_reset:
            agent.reset_history()
            detector.record_reset(agent.turn_count)
            reset_triggered = True
            reset_reason = reason
            
            response += "\n\n[System: I've cleared my conversation history to provide you with a fresh start. How can I help you?]"
        
        return ChatResponse(
            response=response,
            reset_triggered=reset_triggered,
            reset_reason=reset_reason,
            stats=agent_stats
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/stats", response_model=StatsResponse)
async def get_stats(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    agent = session["agent"]
    detector = session["detector"]
    device = session["device"]
    
    return StatsResponse(
        agent_stats=agent.get_stats(),
        detector_stats=detector.get_stats(),
        device_status=device.get_status()
    )


@app.get("/session/{session_id}/history")
async def get_history(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return {"history": session["conversation_log"]}


@app.post("/session/{session_id}/device/inject-failure")
async def inject_failure(session_id: str, request: FailureRequest):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    device = session["device"]
    
    try:
        if request.failure_type == "offline":
            device.inject_failure(DeviceState.OFFLINE, request.duration)
        elif request.failure_type == "timeout":
            device.inject_failure(DeviceState.TIMEOUT, request.duration)
        else:
            raise HTTPException(status_code=400, detail="Invalid failure type")
        
        return {"message": f"Injected {request.failure_type} failure for {request.duration} operations"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/device/clear-failure")
async def clear_failure(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    device = session["device"]
    device.clear_failure()
    
    return {"message": "Device failures cleared"}


@app.get("/session/{session_id}/device/status")
async def get_device_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    device = session["device"]
    
    return device.get_status()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
