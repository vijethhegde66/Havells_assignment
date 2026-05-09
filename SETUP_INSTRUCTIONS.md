# Setup Instructions for Evaluators

## Quick Setup (5 Minutes)

### Step 1: Install Dependencies or activate the virtual environment(venv recommonded)

```bash
cd havells_app
pip install -r requirements.txt
```
or 
```bash
havells_app\havells_assign\Scripts\activate
```

### Step 2: Configure Azure OpenAI

Create a `.env` file in the project root or edit the existing one:



Edit `.env` with your Azure OpenAI credentials:

```
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

**Note:** This project uses GPT-4o. Ensure your Azure OpenAI resource has GPT-4o deployed.

### Step 3: Run Evaluation (for checking the all scenarios for evaluation)

```bash
python scenarios.py
```
### IMP : if you want to evaluate using UI please run the below file and copy paste the local URL in the browser

```bash
havells_app_2\havells_app\start_all.bat

```
This will:
- Execute all 5 evaluation scenarios
- Generate transcripts in `test_transcripts/` directory
- Display results with latency metrics
- Create `test_transcripts/SUMMARY.md`

---

## What to Verify

### 1. Scenario 3 (Core Requirement)

Check `test_transcripts/scenario_scenario_3.md`:

**Expected behavior:**
- Turn 1: Tool fails with error
- Turn 2-3: Agent parrots error WITHOUT calling tool (poisoning)
- Turn 3: Reset triggered with reason "stale_error_parroting"
- Turn 4: Tool called successfully (recovery)

**Key indicators:**
- Tool calls: 1 → 1 → 1 → 2
- Resets: 1
- Reset reason: "stale_error_parroting" or "tool_starvation"

### 2. Latency Budget

Check `test_transcripts/SUMMARY.md`:

**Expected metrics:**
- Mean latency: <100ms (typically ~40ms)
- Max latency: <200ms (typically ~90ms)
- P95 latency: <150ms (typically ~60ms)
- Within budget: ✓ (all calls <500ms)

### 3. All Scenarios

Verify all 5 scenarios completed:
- Scenario 1: 0 resets (clean operation)
- Scenario 2: 0-1 resets (transient failure)
- Scenario 3: 1 reset (stale-failure poisoning) ⭐
- Scenario 4: 0-2 resets (repeated failures)
- Scenario 5: 0 resets (mixed intent)

---

## Alternative: Interactive Testing

```bash
python main.py
```

**Test Scenario 3 manually:**

1. Type: `Turn on the fan` (will fail if you inject failure first)
2. Type: `Can you turn on the fan?` (agent should parrot error)
3. Type: `Please turn on the fan` (reset should trigger)
4. Type: `Turn on the fan now` (should succeed after reset)

---

## Troubleshooting

### "Missing required configuration"
→ Create `.env` file with Azure OpenAI credentials

### "Module not found"
→ Run: `pip install -r requirements.txt`

### Scenarios fail
→ Verify Azure OpenAI credentials are correct
→ Check GPT-4o deployment exists

### Latency >500ms
→ Check network connection to Azure
→ Verify no rate limiting

---

## Expected Output

```
Running Scenario: Scenario 3: Stale-Failure Poisoning
...
Turn 1 - User: Turn on the fan
Agent: The device is currently offline...
Turn 2 - User: Can you turn on the fan?
Agent: The device is still offline...
Turn 3 - User: Please turn on the fan
🔄 RESET TRIGGERED: stale_error_parroting
Turn 4 - User: Turn on the fan now
Agent: I've turned on the fan successfully.

Statistics:
- Total turns: 4
- Tool calls: 2
- Resets triggered: 1
- Mean detection latency: 42.35 ms
- Within Budget: ✓
```

---

## Files to Review

1. **README.md** - Main documentation
2. **DESIGN_NOTE.md** - Design decisions (1 page)
3. **test_transcripts/scenario_scenario_3.md** - Core scenario
4. **test_transcripts/SUMMARY.md** - All results
5. **reset_detector.py** - Implementation

---

**Evaluation time: ~10 minutes**
