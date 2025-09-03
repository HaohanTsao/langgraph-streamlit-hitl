# LangGraph + Streamlit Human-in-the-Loop Demo

A simple, educational demo showing how to implement Human-in-the-Loop workflows with LangGraph and Streamlit.

## 🎯 What This Demonstrates

- **NodeInterrupt**: How to pause workflow execution for human input
- **Event Detection**: Detecting interrupts in the event stream  
- **State Management**: Updating workflow state with human decisions
- **Resume Execution**: Continuing from interruption points

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/HaohanTsao/langgraph-streamlit-hitl.git
cd langgraph-streamlit-hitl

# Install dependencies
pip install -r requirements.txt

# Run the demo
streamlit run app.py
```

## 🔑 Key Concepts Explained

### 1. Triggering Interrupts
```python
# In your workflow node
raise NodeInterrupt(data_for_human)
```

### 2. Detecting Interrupts
```python
# In your Streamlit app
events = list(workflow.stream(input, config))
for event in events:
    if "__interrupt__" in event:
        # Handle the interruption
        interrupt_data = event["__interrupt__"][0].value
```

### 3. Resuming Execution
```python
# Update state with human decision
workflow.update_state(config, {"decision": "approved"})

# Resume from interruption (note the None input)
workflow.stream(None, config)
```

## ⚠️ Common Pitfalls

1. **Don't confuse `astream_events` with `stream`**
   - `astream_events`: For monitoring/UI updates
   - `stream`: For actual execution

2. **Interrupts are events, not exceptions**
   - Look for `__interrupt__` in events
   - Don't try to catch NodeInterrupt with try/except

3. **Use `None` when resuming**
   - `stream(None, config)` resumes from interruption
   - `stream(new_input, config)` starts fresh

## 🧠 How It Works

1. **User Input** → Workflow analyzes task risk level
2. **High Risk Detected** → `NodeInterrupt` pauses execution  
3. **Human Decision** → User approves/rejects via Streamlit UI
4. **Resume** → Workflow continues with human decision
5. **Final Result** → Task completed based on approval

## 📚 Learn More

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Human-in-the-Loop Patterns](https://langchain-ai.github.io/langgraph/tutorials/get-started/4-human-in-the-loop/)
