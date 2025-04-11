import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import uuid
import math

# Import custom modules (relative imports from current package)
from get_response import OpenAIClient
from chroma_agent import ChromaAgent
from assign_agent import AssignAgent
from summarization_agent import SummarizationAgent
from admin.dynamic_ticketing import DynamicTicketing  # Fixed import path
from prompts import followup_agent_prompt

# Set page config
st.set_page_config(
    page_title="Support Issue Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Function to format time nicely
def format_time(hours):
    """Format time in a user-friendly way - use days if over 24 hours"""
    if hours >= 24:
        days = hours / 24
        return f"{math.ceil(days)} days"
    else:
        return f"{math.ceil(hours)} hours"

# Function to handle chat message submission
def handle_chat_message():
    message = st.session_state.chat_input
    if not message:
        return
    
    # Add user message to chat history
    st.session_state.chat_history.append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Also update the conversation in TinyDB if we have a ticket ID
    if "ticket_id" in st.session_state and st.session_state.ticket_id:
        st.session_state.ticket_system.update_conversation(
            st.session_state.ticket_id, 
            message, 
            "user"
        )
    
    # Check if this is a follow-up question
    is_followup = len(st.session_state.chat_history) > 2 and st.session_state.issue_summary is not None
    
    if is_followup:
        # Handle follow-up question
        handle_followup_question(message)
    else:
        # Handle initial question
        handle_initial_question(message)

def handle_initial_question(message):
    """Process an initial question from the user"""
    # 1. Summarize the issue
    with st.spinner("Analyzing issue..."):
        summary_result = st.session_state.summarization_agent.summarize_issue(message)
        st.session_state.issue_summary = summary_result
        st.session_state.initial_question = message
    
    # 2. Find similar issues using ChromaDB
    with st.spinner("Finding similar issues..."):
        similar_issues = st.session_state.chroma_agent.query(summary_result["summary"], n_results=5)
        st.session_state.similar_issues = similar_issues
    
    # 3. Assign team and estimate resolution time
    with st.spinner("Assigning team..."):
        # Simple context for initial questions
        api_chat_history = [
            {"role": "system", "content": f"The user's issue has been summarized as: '{summary_result['summary']}'."}
        ]
        
        assignment_result = st.session_state.assign_agent.process_and_assign(
            message,
            chat_history=api_chat_history,
            n_results=3
        )
        st.session_state.assignment_result = assignment_result
    
    # Create a ticket ID for this conversation
    with st.spinner("Creating ticket..."):
        # Create a ticket in the ticketing system
        if "ticket_id" not in st.session_state or not st.session_state.ticket_id:
            ticket_id = st.session_state.ticket_system.create_new_ticket(
                issue_summary=summary_result["summary"],
                sentiment=summary_result["sentiment"],
                priority=summary_result["priority"],
                assigned_team=assignment_result.get("assigned_team", "Support")
            )
            st.session_state.ticket_id = ticket_id
            
            # Add both the user message and initial response to the ticket
            st.session_state.ticket_system.update_conversation(
                ticket_id, 
                message, 
                "user"
            )
    
    # Add system response to chat history
    if st.session_state.assignment_result["source"] == "historical_data":
        resolution_hours = st.session_state.assignment_result['estimated_resolution_hours']
        formatted_time = format_time(resolution_hours)
        response_content = (
            f"I've analyzed your issue which appears to be about '{summary_result['summary']}'. "
            f"Here's a suggested solution: {summary_result['solution']}\n\n"
            f"Estimated resolution time: {formatted_time}\n\n"
            f"Is this helpful? If not, I can create a support ticket for you."
        )
    else:  # LLM source
        resolution_hours = st.session_state.assignment_result.get('estimated_resolution_hours', 24)
        formatted_time = format_time(resolution_hours)
        response_content = (
            f"I've analyzed your issue which appears to be about '{summary_result['summary']}'. "
            f"Here's a suggested solution: {summary_result['solution']}\n\n"
            f"Estimated resolution time: {formatted_time}\n\n"
            f"Is this helpful? If not, I can create a support ticket for you."
        )
    
    # Add the assistant response to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response_content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Also update the conversation in TinyDB
    if "ticket_id" in st.session_state and st.session_state.ticket_id:
        st.session_state.ticket_system.update_conversation(
            st.session_state.ticket_id,
            response_content,
            "assistant"
        )
    
    # Update the issue analysis panel
    st.session_state.show_analysis = True
    
    # Enable feedback buttons
    st.session_state.show_feedback = True
    
    # Extract common solutions to display on the left
    extract_common_solutions()
    
def handle_followup_question(message):
    """Process a follow-up question using context from previous interactions"""
    with st.spinner("Processing your follow-up question..."):
        # Get last 3 conversations for context
        recent_messages = get_recent_context(3)
        conversation_summary = "\n".join([f"{m['role']}: {m['content']}" for m in recent_messages])
        
        # Get assigned team from previous interaction
        if st.session_state.assignment_result:
            if st.session_state.assignment_result["source"] == "historical_data":
                assigned_team = st.session_state.assignment_result['assigned_team']
            else:
                assigned_team = st.session_state.assignment_result.get('assigned_team', "support")
        else:
            assigned_team = "support"
        
        # Create the follow-up prompt
        followup_prompt = followup_agent_prompt()
        user_prompt = followup_prompt.user_prompt.format(
            conversation_summary=conversation_summary,
            initial_question=st.session_state.initial_question,
            issue_summary=st.session_state.issue_summary['summary'],
            suggested_solution=st.session_state.issue_summary['solution'],
            assigned_team=assigned_team,
            followup_question=message
        )
        
        # Get response from LLM for follow-up
        followup_response = st.session_state.openai_client.get_response(
            user_prompt, 
            followup_prompt.system_prompt, 
            []  # No chat history needed as context is in the prompt
        )
        
        # Add response to chat history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": followup_response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Also update the conversation in TinyDB
        if "ticket_id" in st.session_state and st.session_state.ticket_id:
            st.session_state.ticket_system.update_conversation(
                st.session_state.ticket_id,
                followup_response,
                "assistant"
            )

def mark_resolved():
    """Mark the issue as resolved"""
    st.session_state.issue_resolved = True
    st.session_state.show_feedback = False
    
    # Add resolution message to chat history
    resolution_message = "Great! I'm glad I could help solve your issue. Is there anything else you need help with?"
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": resolution_message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Update ticket in TinyDB as resolved
    if "ticket_id" in st.session_state and st.session_state.ticket_id:
        # Get the solution that was provided
        solution = ""
        if st.session_state.issue_summary and 'solution' in st.session_state.issue_summary:
            solution = st.session_state.issue_summary['solution']
        
        # Mark ticket as resolved in TinyDB
        st.session_state.ticket_system.mark_as_resolved(
            st.session_state.ticket_id,
            solution
        )
        
        # Add final resolution message to TinyDB
        st.session_state.ticket_system.update_conversation(
            st.session_state.ticket_id,
            resolution_message,
            "assistant"
        )

def request_human_agent():
    """Create a support ticket and forward to human agent"""
    st.session_state.human_agent_requested = True
    st.session_state.show_feedback = False
    
    # We already have a ticket ID, so just use that
    if "ticket_id" not in st.session_state or not st.session_state.ticket_id:
        # This should not happen as we create a ticket ID on first message
        st.error("Error: No ticket ID found")
        return
    
    # Flag the ticket for human assistance
    st.session_state.ticket_system.flag_for_human_agent(st.session_state.ticket_id)
    
    # Calculate estimated resolution time
    if st.session_state.assignment_result:
        if st.session_state.assignment_result["source"] == "historical_data":
            est_hours = st.session_state.assignment_result['estimated_resolution_hours']
        else:
            est_hours = st.session_state.assignment_result.get('estimated_resolution_hours', 24)
    else:
        est_hours = 24  # default
    
    formatted_time = format_time(est_hours)
    
    # Add ticket created message to chat history
    ticket_message = (
        f"I've created a support ticket for you (#{st.session_state.ticket_id}). "
        f"A human agent from our {st.session_state.assignment_result.get('assigned_team', 'support')} team "
        f"will contact you shortly. The estimated resolution time is {formatted_time}. Thank you for your patience."
    )
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": ticket_message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Add message to TinyDB conversation
    st.session_state.ticket_system.update_conversation(
        st.session_state.ticket_id,
        ticket_message,
        "assistant"
    )

def extract_common_solutions():
    """Extract common solutions from similar issues to display on the left"""
    if not st.session_state.similar_issues:
        return
    
    # Extract solutions from similar issues
    common_solutions = []
    for issue in st.session_state.similar_issues:
        if issue['similarity_score'] >= 0.3:  # Only use reasonably similar issues
            solution = {
                "issue": issue['issue'],
                "solution": issue['metadata']['solution'],
                "similarity": issue['similarity_score']
            }
            common_solutions.append(solution)
    
    # Sort by similarity score and take top 3
    common_solutions.sort(key=lambda x: x['similarity'], reverse=True)
    st.session_state.common_solutions = common_solutions[:3]

# Helper function to get recent messages for context
def get_recent_context(num_messages=3):
    """Get the most recent messages from chat history for context"""
    messages = []
    
    # Get only user and assistant messages (not system)
    user_assistant_msgs = [msg for msg in st.session_state.chat_history 
                         if msg["role"] in ["user", "assistant"]]
    
    # Take up to the last num_messages
    recent = user_assistant_msgs[-num_messages:] if len(user_assistant_msgs) > num_messages else user_assistant_msgs
    
    for msg in recent:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    return messages

# Helper function to get full conversation history
def get_full_context():
    """Get the full conversation history for better context understanding"""
    messages = []
    
    # Get only user and assistant messages (not system)
    user_assistant_msgs = [msg for msg in st.session_state.chat_history 
                         if msg["role"] in ["user", "assistant"]]
    
    for msg in user_assistant_msgs:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    return messages

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "issue_summary" not in st.session_state:
    st.session_state.issue_summary = None

if "initial_question" not in st.session_state:
    st.session_state.initial_question = None

if "similar_issues" not in st.session_state:
    st.session_state.similar_issues = None

if "common_solutions" not in st.session_state:
    st.session_state.common_solutions = []

if "assignment_result" not in st.session_state:
    st.session_state.assignment_result = None

if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False

if "show_feedback" not in st.session_state:
    st.session_state.show_feedback = False

if "issue_resolved" not in st.session_state:
    st.session_state.issue_resolved = False

if "human_agent_requested" not in st.session_state:
    st.session_state.human_agent_requested = False

if "ticket_id" not in st.session_state:
    st.session_state.ticket_id = None

# Initialize agents
if "openai_client" not in st.session_state:
    st.session_state.openai_client = OpenAIClient()

if "chroma_agent" not in st.session_state:
    st.session_state.chroma_agent = ChromaAgent()

if "summarization_agent" not in st.session_state:
    st.session_state.summarization_agent = SummarizationAgent(
        st.session_state.openai_client
    )

if "assign_agent" not in st.session_state:
    st.session_state.assign_agent = AssignAgent(
        st.session_state.openai_client,
        st.session_state.chroma_agent,
        st.session_state.summarization_agent
    )

# Initialize the ticket system
if "ticket_system" not in st.session_state:
    st.session_state.ticket_system = DynamicTicketing()

# Preload historical data if needed
if "data_loaded" not in st.session_state:
    try:
        # Check if we need to load data
        count = st.session_state.chroma_agent.collection.count()
        if count == 0:
            print("No data in ChromaDB, loading historical data...")
            # Try to load data from the expected location
            csv_path = "app/chat_history/historical_ticket_new.csv"
            if os.path.exists(csv_path):
                records = st.session_state.chroma_agent.load_data_from_csv(csv_path)
                print(f"Loaded {records} records into ChromaDB")
            else:
                print(f"Warning: Historical data file not found at {csv_path}")
        else:
            print(f"ChromaDB already contains {count} documents")
    except Exception as e:
        print(f"Error preloading data: {str(e)}")
    st.session_state.data_loaded = True

# Main layout with two columns
col1, col2 = st.columns([1, 2])

# Left column - Common solutions
with col1:
    st.title("Common Fixes")
    
    # Display current ticket ID if available
    if "ticket_id" in st.session_state and st.session_state.ticket_id:
        st.info(f"Current ticket: {st.session_state.ticket_id}")
    
    if st.session_state.common_solutions:
        for i, solution in enumerate(st.session_state.common_solutions):
            with st.container():
                st.subheader(f"Solution {i+1}")
                st.write(f"**Issue**: {solution['issue']}")
                st.write(f"**Fix**: {solution['solution']}")
                st.markdown("---")
    else:
        st.info("Ask a question to see common solutions that worked for similar issues.")

# Right column - Chat interface
with col2:
    st.title("Smart Home Support Chat")
    
    # Chat container
    chat_container = st.container()
    
    # Display chat messages
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").write(f"{msg['content']}")
            else:
                st.chat_message("assistant").write(f"{msg['content']}")
    
    # Feedback buttons (only show after a response and if not already resolved or escalated)
    if st.session_state.show_feedback and not st.session_state.issue_resolved and not st.session_state.human_agent_requested:
        col_yes, col_no = st.columns(2)
        with col_yes:
            st.button("Yes, this helped! ✓", on_click=mark_resolved, key="btn_resolved")
        with col_no:
            st.button("No, I need a human agent", on_click=request_human_agent, key="btn_human")
    
    # Show ticket information if human agent was requested
    if st.session_state.human_agent_requested and st.session_state.ticket_id:
        # Calculate estimated resolution time
        if st.session_state.assignment_result:
            if st.session_state.assignment_result["source"] == "historical_data":
                est_hours = st.session_state.assignment_result['estimated_resolution_hours']
            else:
                est_hours = st.session_state.assignment_result.get('estimated_resolution_hours', 24)
        else:
            est_hours = 24  # default
            
        formatted_time = format_time(est_hours)
        st.success(f"Ticket #{st.session_state.ticket_id} has been created. A support agent will contact you within {formatted_time}.")
    
    # Chat input at the bottom
    st.chat_input(
        placeholder="Ask about any issues with your smart home devices...",
        key="chat_input",
        on_submit=handle_chat_message,
        disabled=st.session_state.human_agent_requested  # Disable input if ticket created
    )

# Simplified sidebar with just issue analysis
with st.sidebar:
    st.title("Technical Details")
    
    # Show analysis details in sidebar if available
    if st.session_state.issue_summary and st.session_state.show_analysis:
        st.subheader("Issue Analysis")
        st.write(f"**Summary**: {st.session_state.issue_summary['summary']}")
        st.write(f"**Sentiment**: {st.session_state.issue_summary['sentiment']}")
        st.write(f"**Priority**: {st.session_state.issue_summary['priority']}")
        
        if st.session_state.assignment_result:
            if st.session_state.assignment_result["source"] == "historical_data":
                est_hours = st.session_state.assignment_result['estimated_resolution_hours']
                formatted_time = format_time(est_hours)
                st.write(f"**Team**: {st.session_state.assignment_result['assigned_team']}")
                st.write(f"**Est. Resolution**: {formatted_time}")
                st.write(f"**Confidence**: {st.session_state.assignment_result['confidence_score']:.2f}")
                st.write(f"**Source**: Based on historical similar cases")
            elif "assigned_team" in st.session_state.assignment_result:
                est_hours = st.session_state.assignment_result.get('estimated_resolution_hours', 24)
                formatted_time = format_time(est_hours)
                st.write(f"**Team**: {st.session_state.assignment_result['assigned_team']}")
                st.write(f"**Est. Resolution**: {formatted_time}")
                st.write(f"**Source**: AI recommendation")
    else:
        st.info("Ask a question to see technical analysis details here.") 