import streamlit as st
from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import NodeInterrupt

# ============= State Definition =============
class WorkflowState(TypedDict):
    task: str
    approval_status: Optional[str]
    result: Optional[str]
    iteration: int

# ============= Graph Nodes =============
def analyze_task(state: WorkflowState) -> WorkflowState:
    """Analyze task and determine if human approval is needed"""
    task = state["task"]
    iteration = state.get("iteration", 0)
    
    # Skip approval if task was modified (second iteration)
    if iteration > 0:
        return {**state, "approval_status": "modified"}
    
    # Check for sensitive keywords that require approval
    sensitive_keywords = ["delete", "remove", "critical", "important", "sensitive"]
    needs_approval = any(keyword in task.lower() for keyword in sensitive_keywords)
    
    if needs_approval:
        # Trigger human-in-the-loop
        raise NodeInterrupt(
            f"🔔 Task requires human approval:\n"
            f"📋 Task: {task}\n"
            f"Please choose: Approve / Reject / Modify"
        )
    
    return {**state, "approval_status": "auto_approved"}

def execute_task(state: WorkflowState) -> WorkflowState:
    """Execute the approved task"""
    task = state["task"]
    approval_status = state.get("approval_status", "unknown")
    
    # Generate result based on approval status
    status_messages = {
        "approved": f"✅ Task approved and executed:\n📋 {task}",
        "modified": f"📝 Modified task executed successfully:\n📋 {task}",
        "auto_approved": f"✅ Task auto-approved and executed:\n📋 {task}"
    }
    
    result = status_messages.get(approval_status, f"✅ Task completed:\n📋 {task}")
    
    return {**state, "result": result}

def handle_rejection(state: WorkflowState) -> WorkflowState:
    """Handle rejected task"""
    return {
        **state,
        "result": f"❌ Task rejected and not executed:\n📋 {state['task']}"
    }

# ============= Conditional Routing =============
def route_after_analyze(state: WorkflowState) -> Literal["execute", "reject"]:
    """Route based on approval status"""
    approval_status = state.get("approval_status", "")
    return "reject" if approval_status == "rejected" else "execute"

# ============= Build Workflow =============
def create_workflow():
    """Create and compile the workflow graph"""
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_task)
    workflow.add_node("execute", execute_task)
    workflow.add_node("reject", handle_rejection)
    
    # Add edges
    workflow.add_edge(START, "analyze")
    workflow.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"execute": "execute", "reject": "reject"}
    )
    workflow.add_edge("execute", END)
    workflow.add_edge("reject", END)
    
    # Add checkpointer for interruptions
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# ============= Streamlit UI =============
def main():
    st.set_page_config(
        page_title="LangGraph Human-in-the-Loop Demo",
        page_icon="🤖",
        layout="centered"
    )
    
    st.title("🤖 LangGraph Human-in-the-Loop Demo")
    st.markdown("A simple example of workflow interruption and human decision making")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "is_interrupted" not in st.session_state:
        st.session_state.is_interrupted = False
    if "current_task" not in st.session_state:
        st.session_state.current_task = ""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = "demo_thread"
    if "workflow" not in st.session_state:
        st.session_state.workflow = create_workflow()
    
    # Sidebar with instructions
    with st.sidebar:
        st.header("📋 Try These Examples")
        st.markdown("""
        **🟢 Auto-Execute (Safe):**
        - `process data`
        - `send email`
        - `generate report`
        
        **🔴 Requires Approval:**
        - `delete important file`
        - `remove critical data`
        - `process sensitive information`
        
        **⚙️ How it works:**
        1. Enter a task
        2. System analyzes for sensitive content
        3. If sensitive → Human approval required
        4. Choose: Approve / Reject / Modify
        """)
        
        if st.button("🔄 Clear Chat", use_container_width=True):
            clear_conversation()
    
    # Display message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Handle interruption UI
    if st.session_state.is_interrupted:
        st.info("⏸️ Workflow paused - Waiting for your decision...")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Approve", type="primary", use_container_width=True):
                resume_workflow("approved")
        
        with col2:
            if st.button("❌ Reject", use_container_width=True):
                resume_workflow("rejected")
        
        with col3:
            if st.button("📝 Modify", use_container_width=True):
                st.session_state.show_modify = True
                st.rerun()
        
        # Show modification input if requested
        if getattr(st.session_state, 'show_modify', False):
            with st.container(border=True):
                new_task = st.text_input(
                    "Modify task to:",
                    value=st.session_state.current_task,
                    key="modify_input"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Submit", type="primary"):
                        if new_task and new_task != st.session_state.current_task:
                            modify_and_resume(new_task)
                with col2:
                    if st.button("❌ Cancel"):
                        st.session_state.show_modify = False
                        st.rerun()
    
    # Task input (only show when not interrupted)
    elif task := st.chat_input("Enter a task (e.g., 'delete important file')"):
        process_new_task(task)

def process_new_task(task: str):
    """Process a new task through the workflow"""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": f"Execute: {task}"})
    st.session_state.current_task = task
    
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    initial_state = {"task": task, "approval_status": None, "result": None, "iteration": 0}
    
    try:
        # Run workflow
        events = list(st.session_state.workflow.stream(initial_state, config))
        
        # Check for interruptions
        interrupted = False
        for event in events:
            if "__interrupt__" in event:
                interrupt_message = event["__interrupt__"][0].value
                st.session_state.messages.append({"role": "assistant", "content": interrupt_message})
                st.session_state.is_interrupted = True
                interrupted = True
                break
        
        # If not interrupted, get the result
        if not interrupted:
            state = st.session_state.workflow.get_state(config)
            if result := state.values.get("result"):
                st.session_state.messages.append({"role": "assistant", "content": result})
                
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"❗ Error: {str(e)}"})
    
    st.rerun()

def resume_workflow(decision: str):
    """Resume workflow execution with human decision"""
    # Add user decision message
    decision_text = {"approved": "✅ Approved", "rejected": "❌ Rejected"}
    st.session_state.messages.append({"role": "user", "content": decision_text[decision]})
    
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    
    # Update state and resume
    st.session_state.workflow.update_state(config, {"approval_status": decision})
    
    try:
        # Resume from interruption point (note the None input)
        list(st.session_state.workflow.stream(None, config))
        
        # Get final result
        state = st.session_state.workflow.get_state(config)
        if result := state.values.get("result"):
            st.session_state.messages.append({"role": "assistant", "content": result})
            
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"❗ Resume error: {str(e)}"})
    
    # Clear interruption state
    st.session_state.is_interrupted = False
    if hasattr(st.session_state, 'show_modify'):
        del st.session_state.show_modify
    st.rerun()

def modify_and_resume(new_task: str):
    """Modify task and resume execution"""
    # Add modification message
    st.session_state.messages.append({"role": "user", "content": f"📝 Modified to: {new_task}"})
    st.session_state.current_task = new_task
    
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    
    # Update state with modified task (iteration=1 to skip re-approval)
    st.session_state.workflow.update_state(config, {
        "task": new_task,
        "approval_status": "modified",
        "iteration": 1
    })
    
    try:
        # Resume execution
        list(st.session_state.workflow.stream(None, config))
        
        # Get result
        state = st.session_state.workflow.get_state(config)
        if result := state.values.get("result"):
            st.session_state.messages.append({"role": "assistant", "content": result})
            
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"❗ Modify error: {str(e)}"})
    
    # Clear states
    st.session_state.is_interrupted = False
    st.session_state.show_modify = False
    st.rerun()

def clear_conversation():
    """Clear conversation and reset state"""
    st.session_state.messages = []
    st.session_state.is_interrupted = False
    st.session_state.current_task = ""
    st.session_state.workflow = create_workflow()
    if hasattr(st.session_state, 'show_modify'):
        del st.session_state.show_modify
    st.rerun()

if __name__ == "__main__":
    main()