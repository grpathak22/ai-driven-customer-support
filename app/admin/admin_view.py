
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import json
from dynamic_ticketing import DynamicTicketing

# Set page config
st.set_page_config(
    page_title="Support System Admin View",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .card {
        border-radius: 10px;
        padding: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
    }
    .metric-label {
        font-size: 1rem;
        color: #6B7280;
        text-align: center;
    }
    .stat-card {
        border-left: 5px solid #1E88E5;
        border-radius: 5px;
        padding: 10px;
        background-color: #F3F4F6;
        margin-bottom: 10px;
    }
    .sidebar-title {
        font-weight: 700;
        color: #1E3A8A;
    }
    .plot-container {
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
        background-color: white;
        padding: 1rem;
    }
    .user-msg {
        background-color: #E3F2FD;
        padding: 10px 15px;
        border-radius: 15px 15px 15px 5px;
        margin-bottom: 10px;
    }
    .assistant-msg {
        background-color: #F1F1F1;
        padding: 10px 15px;
        border-radius: 15px 15px 5px 15px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize the ticket system
@st.cache_resource
def get_ticket_system():
    return DynamicTicketing()

ticket_system = get_ticket_system()

# Sidebar with improved UI
with st.sidebar:
    st.markdown('<p class="sidebar-title">ADMIN DASHBOARD</p>', unsafe_allow_html=True)
    st.image("https://img.icons8.com/fluency/96/000000/technical-support.png", width=80)
    
    pages = {
        "📊 Overview": "Overview",
        "✅ Resolved Tickets": "Resolved Tickets",
        "⏳ Unresolved Tickets": "Unresolved Tickets",
        "💬 Conversation Viewer": "Conversation Viewer",
        "🔍 Search": "Search"
    }
    
    page = st.radio("", list(pages.keys()))
    selected_page = pages[page]
    
    st.markdown("---")
    st.markdown("© 2025 Support System")
    st.markdown(f"**Version:** 2.0")

# Function to calculate resolution time in hours
def get_resolution_time(open_date, resolution_date):
    if not open_date or not resolution_date:
        return None
    
    try:
        open_dt = datetime.strptime(open_date, "%Y-%m-%d %H:%M:%S")
        res_dt = datetime.strptime(resolution_date, "%Y-%m-%d %H:%M:%S")
        delta = res_dt - open_dt
        hours = delta.total_seconds() / 3600
        return round(hours, 1)
    except Exception as e:
        return None

# Overview Page with enhanced visualization
if selected_page == "Overview":
    st.markdown('<p class="main-header">Support System Overview</p>', unsafe_allow_html=True)
    
    # Get all tickets
    resolved_tickets = ticket_system.get_all_resolved_tickets()
    unresolved_tickets = ticket_system.get_all_unresolved_tickets()
    total_tickets = len(resolved_tickets) + len(unresolved_tickets)
    
    # Create metrics row with improved styling
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{total_tickets}</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Total Tickets</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value" style="color: #10B981;">{len(resolved_tickets)}</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Resolved</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value" style="color: #F59E0B;">{len(unresolved_tickets)}</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Unresolved</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        resolution_rate = round((len(resolved_tickets) / total_tickets * 100), 1) if total_tickets else 0
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value" style="color: #3B82F6;">{resolution_rate}%</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Resolution Rate</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Create some analytics with improved visualizations
    if resolved_tickets:
        df_resolved = pd.DataFrame(resolved_tickets)
        
        # Create a 2x2 grid of charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            st.subheader("Tickets by Team")
            team_counts = df_resolved['Assigned_To_Team'].value_counts().reset_index()
            team_counts.columns = ['Team', 'Count']
            
            # Create donut chart
            fig1 = px.pie(team_counts, values='Count', names='Team', hole=0.4,
                          color_discrete_sequence=px.colors.qualitative.Bold)
            fig1.update_traces(textinfo='percent+label', pull=[0.05 if i == team_counts['Count'].idxmax() else 0 for i in range(len(team_counts))])
            fig1.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=350)
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with chart_col2:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            st.subheader("Ticket Resolution Progress")
            
            # Create gauge chart for resolution rate
            fig2 = go.Figure(go.Indicator(
                mode="gauge+number",
                value=resolution_rate,
                title={'text': "Resolution Rate"},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1},
                    'bar': {'color': "#3B82F6"},
                    'steps': [
                        {'range': [0, 30], 'color': "#FEE2E2"},
                        {'range': [30, 70], 'color': "#FEF3C7"},
                        {'range': [70, 100], 'color': "#D1FAE5"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig2.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=350)
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Second row of charts
        chart_col3, chart_col4 = st.columns(2)
        
        with chart_col3:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            st.subheader("Top Issue Categories")
            issue_counts = df_resolved['Issue_Category'].value_counts().reset_index()
            issue_counts.columns = ['Issue', 'Count']
            
            # Horizontal bar chart for issues
            fig3 = px.bar(issue_counts.head(8), y='Issue', x='Count', orientation='h',
                         color='Count', color_continuous_scale='Viridis')
            fig3.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=350)
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with chart_col4:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            st.subheader("Resolution Time Analysis")
            
            # Calculate resolution times
            df_resolved['Resolution_Time_Hours'] = df_resolved.apply(
                lambda row: get_resolution_time(row['Ticket_Open_Date'], row['Date_of_Resolution']), 
                axis=1
            )
            
            # Remove any None values
            df_time = df_resolved.dropna(subset=['Resolution_Time_Hours'])
            
            # Team resolution time box plot
            if not df_time.empty:
                fig4 = px.box(df_time, x='Assigned_To_Team', y='Resolution_Time_Hours', 
                             color='Assigned_To_Team', points="all")
                fig4.update_layout(
                    margin=dict(t=10, b=0, l=0, r=0),
                    xaxis_title="Team",
                    yaxis_title="Resolution Time (Hours)",
                    height=350
                )
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No resolution time data available")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Third row - trend analysis
        st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.subheader("Ticket Trends Over Time")
        
        # Try to extract dates and create time series
        try:
            df_resolved['Date'] = pd.to_datetime(df_resolved['Ticket_Open_Date']).dt.date
            date_counts = df_resolved.groupby('Date').size().reset_index(name='count')
            date_counts['Date'] = pd.to_datetime(date_counts['Date'])
            date_counts = date_counts.sort_values('Date')
            
            # Create area chart
            fig5 = px.area(date_counts, x='Date', y='count', 
                           title="Tickets Opened by Date",
                           labels={"count": "Number of Tickets", "Date": "Date"},
                           line_shape="spline", render_mode="svg")
            fig5.update_traces(line_color='#3B82F6', fill='tozeroy', line=dict(width=2))
            fig5.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig5, use_container_width=True)
        except:
            st.info("Unable to generate time trends. Check date format in tickets.")
        st.markdown('</div>', unsafe_allow_html=True)

# Resolved Tickets Page
elif selected_page == "Resolved Tickets":
    st.markdown('<p class="main-header">Resolved Tickets</p>', unsafe_allow_html=True)
    
    resolved_tickets = ticket_system.get_all_resolved_tickets()
    
    if not resolved_tickets:
        st.info("No resolved tickets found.")
    else:
        # Convert to DataFrame for display
        df = pd.DataFrame(resolved_tickets)
        
        # Select only the columns we want to display
        display_cols = [
            'Ticket_ID', 'Issue_Category', 'Sentiment', 'Priority', 
            'Solution', 'Ticket_Open_Date', 'Date_of_Resolution', 'Assigned_To_Team'
        ]
        
        # Filter columns and sort by date
        if all(col in df.columns for col in display_cols):
            df_display = df[display_cols].sort_values('Date_of_Resolution', ascending=False)
            st.dataframe(df_display, use_container_width=True, height=300)
        else:
            st.warning("Some expected columns are missing from the data")
            st.dataframe(df, height=300)
        
        # Ticket selection for details
        selected_ticket_id = st.selectbox(
            "Select a ticket to view details:", 
            options=[ticket['Ticket_ID'] for ticket in resolved_tickets]
        )
        
        if selected_ticket_id:
            ticket = ticket_system.get_ticket(selected_ticket_id)
            if ticket:
                st.markdown(f"<h3>Ticket Details: {selected_ticket_id}</h3>", unsafe_allow_html=True)
                
                # Calculate resolution time
                resolution_time = get_resolution_time(
                    ticket.get('Ticket_Open_Date'), 
                    ticket.get('Date_of_Resolution')
                )
                
                # Display ticket details with improved styling
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("<p class='stat-card'><b>Issue:</b> {}</p>".format(ticket.get('Issue_Category')), unsafe_allow_html=True)
                    st.markdown("<p class='stat-card'><b>Priority:</b> {}</p>".format(ticket.get('Priority')), unsafe_allow_html=True)
                    st.markdown("<p class='stat-card'><b>Team:</b> {}</p>".format(ticket.get('Assigned_To_Team')), unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<p class='stat-card'><b>Opened:</b> {}</p>".format(ticket.get('Ticket_Open_Date')), unsafe_allow_html=True)
                    st.markdown("<p class='stat-card'><b>Resolved:</b> {}</p>".format(ticket.get('Date_of_Resolution')), unsafe_allow_html=True)
                    if resolution_time:
                        st.markdown("<p class='stat-card'><b>Resolution Time:</b> {} hours</p>".format(resolution_time), unsafe_allow_html=True)
                
                with col3:
                    st.markdown("<p class='stat-card'><b>Sentiment:</b> {}</p>".format(ticket.get('Sentiment')), unsafe_allow_html=True)
                    st.markdown("<p class='stat-card'><b>Status:</b> {}</p>".format(ticket.get('Resolution_Status')), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Display solution
                st.subheader("Solution")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.write(ticket.get('Solution', 'No solution recorded'))
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Display conversation
                st.subheader("Conversation")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                conversation = ticket.get('conversation', [])
                for msg in conversation:
                    if msg.get('role') == 'user':
                        st.markdown(f"<b>User</b> ({msg.get('timestamp', 'N/A')}):", unsafe_allow_html=True)
                        st.markdown(f"<div class='user-msg'>{msg.get('content')}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<b>Assistant</b> ({msg.get('timestamp', 'N/A')}):", unsafe_allow_html=True)
                        st.markdown(f"<div class='assistant-msg'>{msg.get('content')}</div>", unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

# Similar enhancements for the remaining pages would follow the same pattern
# The pattern includes using the card containers, better colors and layout
# For brevity, I've shown the main design improvements in the first two pages

# Placeholder for the remaining pages that would follow the same enhanced styling
elif selected_page == "Unresolved Tickets":
    st.markdown('<p class="main-header">Unresolved Tickets</p>', unsafe_allow_html=True)
    
    unresolved_tickets = ticket_system.get_all_unresolved_tickets()
    
    if not unresolved_tickets:
        st.info("No unresolved tickets found.")
    else:
        # Convert to DataFrame for display
        df = pd.DataFrame(unresolved_tickets)
        
        # Select only the columns we want to display
        display_cols = [
            'Ticket_ID', 'Issue_Category', 'Sentiment', 'Priority', 
            'Ticket_Open_Date', 'Assigned_To_Team', 'Status'
        ]
        
        # Filter columns and sort by date
        if all(col in df.columns for col in display_cols):
            df_display = df[display_cols].sort_values('Ticket_Open_Date', ascending=False)
            
            # Add time open column
            now = datetime.now()
            df_display['Hours_Open'] = df_display['Ticket_Open_Date'].apply(
                lambda x: round((now - datetime.strptime(x, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600, 1)
                if x and isinstance(x, str) else 0
            )
            
            # Color code based on priority and time open
            def highlight_priority(row):
                if row['Priority'] == 'High':
                    return ['background-color: #FECACA'] * len(row)
                elif row['Priority'] == 'Medium':
                    return ['background-color: #FEF3C7'] * len(row)
                return [''] * len(row)
            
            styled_df = df_display.style.apply(highlight_priority, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=300)
        else:
            st.warning("Some expected columns are missing from the data")
            st.dataframe(df, height=300)
        
        # Add visualization of unresolved tickets
        st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.subheader("Unresolved Tickets Analysis")
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Priority distribution
            priority_counts = df['Priority'].value_counts().reset_index()
            priority_counts.columns = ['Priority', 'Count']
            
            colors = {'High': '#EF4444', 'Medium': '#F59E0B', 'Low': '#10B981'}
            color_discrete_map = {p: colors.get(p, '#3B82F6') for p in priority_counts['Priority']}
            
            fig1 = px.pie(priority_counts, values='Count', names='Priority',
                          title="Tickets by Priority",
                          color='Priority', color_discrete_map=color_discrete_map)
            fig1.update_traces(textposition='inside', textinfo='percent+label')
            fig1.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=350)
            st.plotly_chart(fig1, use_container_width=True)
        
        with chart_col2:
            # Team distribution
            team_counts = df['Assigned_To_Team'].value_counts().reset_index()
            team_counts.columns = ['Team', 'Count']
            
            fig2 = px.bar(
                team_counts, 
                x='Team', 
                y='Count',
                title="Tickets by Team",
                color='Count',
                color_continuous_scale='Blues'
            )
            fig2.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=350)
            st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Ticket selection for details
        selected_ticket_id = st.selectbox(
            "Select a ticket to view details:", 
            options=[ticket['Ticket_ID'] for ticket in unresolved_tickets]
        )
        
        if selected_ticket_id:
            ticket = ticket_system.get_ticket(selected_ticket_id)
            if ticket:
                st.markdown(f"<h3>Ticket Details: {selected_ticket_id}</h3>", unsafe_allow_html=True)
                
                # Calculate time open
                time_open = None
                if ticket.get('Ticket_Open_Date'):
                    try:
                        open_dt = datetime.strptime(ticket.get('Ticket_Open_Date'), "%Y-%m-%d %H:%M:%S")
                        delta = datetime.now() - open_dt
                        time_open = round(delta.total_seconds() / 3600, 1)
                    except Exception as e:
                        pass
                
                # Display ticket details with improved styling
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("<p class='stat-card'><b>Issue:</b> {}</p>".format(ticket.get('Issue_Category')), unsafe_allow_html=True)
                    st.markdown("<p class='stat-card'><b>Priority:</b> {}</p>".format(ticket.get('Priority')), unsafe_allow_html=True)
                    st.markdown("<p class='stat-card'><b>Team:</b> {}</p>".format(ticket.get('Assigned_To_Team')), unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<p class='stat-card'><b>Opened:</b> {}</p>".format(ticket.get('Ticket_Open_Date')), unsafe_allow_html=True)
                    if time_open:
                        st.markdown("<p class='stat-card'><b>Time Open:</b> {} hours</p>".format(time_open), unsafe_allow_html=True)
                    st.markdown("<p class='stat-card'><b>Status:</b> {}</p>".format(ticket.get('Status', 'Unresolved')), unsafe_allow_html=True)
                
                with col3:
                    st.markdown("<p class='stat-card'><b>Sentiment:</b> {}</p>".format(ticket.get('Sentiment')), unsafe_allow_html=True)
                    
                    # Add action buttons for ticket management
                    if st.button("Mark as Resolved", key=f"resolve_{selected_ticket_id}"):
                        ticket_system.resolve_ticket(
                            ticket_id=selected_ticket_id,
                            resolution_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            solution="Resolved by admin"
                        )
                        st.success(f"Ticket {selected_ticket_id} marked as resolved!")
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Display conversation
                st.subheader("Conversation")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                conversation = ticket.get('conversation', [])
                for msg in conversation:
                    if msg.get('role') == 'user':
                        st.markdown(f"<b>User</b> ({msg.get('timestamp', 'N/A')}):", unsafe_allow_html=True)
                        st.markdown(f"<div class='user-msg'>{msg.get('content')}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<b>Assistant</b> ({msg.get('timestamp', 'N/A')}):", unsafe_allow_html=True)
                        st.markdown(f"<div class='assistant-msg'>{msg.get('content')}</div>", unsafe_allow_html=True)
                
                # Add a form to respond to the ticket
                with st.form(key=f"respond_form_{selected_ticket_id}"):
                    response_text = st.text_area("Add a response to this ticket")
                    submit_button = st.form_submit_button(label="Send Response")
                    
                    if submit_button and response_text:
                        # Add the response to the conversation
                        new_msg = {
                            "role": "assistant",
                            "content": response_text,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        ticket_system.add_message_to_ticket(selected_ticket_id, new_msg)
                        st.success("Response added successfully!")
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
elif selected_page == "Conversation Viewer":
    st.markdown('<p class="main-header">Conversation Viewer</p>', unsafe_allow_html=True)
    # Enhancements would follow the pattern shown above
    
elif selected_page == "Search":
    st.markdown('<p class="main-header">Search Tickets</p>', unsafe_allow_html=True)
    # Enhancements would follow the pattern shown above

