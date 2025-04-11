import os
import json
from datetime import datetime
from tinydb import TinyDB, Query
import pandas as pd
import uuid

class DynamicTicketing:
    def __init__(self, db_path="admin/ticket_db.json"):
        """Initialize TinyDB for ticket storage with separate tables for resolved and unresolved tickets"""
        self.db = TinyDB(db_path)
        self.resolved_table = self.db.table('resolved')
        self.unresolved_table = self.db.table('unresolved')
        self.Ticket = Query()
    
    def create_new_ticket(self, issue_summary, sentiment, priority, assigned_team):
        """Create a new ticket and return the ticket ID"""
        # Generate unique ticket ID starting with TECH_
        all_tickets = self.resolved_table.all() + self.unresolved_table.all()
        ticket_numbers = []
        
        for ticket in all_tickets:
            if 'Ticket_ID' in ticket and ticket['Ticket_ID'].startswith('TECH_'):
                try:
                    num = int(ticket['Ticket_ID'].replace('TECH_', ''))
                    ticket_numbers.append(num)
                except ValueError:
                    pass
        
        # Generate next ticket number
        next_num = max(ticket_numbers) + 1 if ticket_numbers else 200
        ticket_id = f"TECH_{next_num}"
        
        # Create new ticket record
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_ticket = {
            "Ticket_ID": ticket_id,
            "Issue_Category": issue_summary,
            "Sentiment": sentiment,
            "Priority": priority,
            "Solution": "",  # Will be filled when resolved
            "Resolution_Status": "Open",
            "Ticket_Open_Date": current_time,
            "Date_of_Resolution": None,
            "Assigned_To_Team": assigned_team,
            "conversation": []  # Will be updated as the conversation progresses
        }
        
        # Insert into unresolved table
        self.unresolved_table.insert(new_ticket)
        return ticket_id
    
    def update_conversation(self, ticket_id, message, role="user"):
        """Add a new message to the conversation history for a ticket"""
        # Check unresolved first, then resolved
        ticket = self.unresolved_table.get(self.Ticket.Ticket_ID == ticket_id)
        table = self.unresolved_table
        
        if not ticket:
            ticket = self.resolved_table.get(self.Ticket.Ticket_ID == ticket_id)
            table = self.resolved_table
            
        if not ticket:
            print(f"Ticket {ticket_id} not found")
            return False
        
        # Update conversation
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_message = {
            "role": role,
            "content": message,
            "timestamp": current_time
        }
        
        # Get current conversation
        conversation = ticket.get('conversation', [])
        conversation.append(new_message)
        
        # Update the ticket with the new conversation
        table.update({"conversation": conversation}, self.Ticket.Ticket_ID == ticket_id)
        return True
    
    def mark_as_resolved(self, ticket_id, solution):
        """Mark a ticket as resolved and move it to the resolved table"""
        # Find the ticket in the unresolved table
        ticket = self.unresolved_table.get(self.Ticket.Ticket_ID == ticket_id)
        
        if not ticket:
            print(f"Unresolved ticket {ticket_id} not found")
            return False
        
        # Update resolution information
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ticket["Resolution_Status"] = "Resolved"
        ticket["Date_of_Resolution"] = current_time
        ticket["Solution"] = solution
        
        # Add to resolved table and remove from unresolved
        self.resolved_table.insert(ticket)
        self.unresolved_table.remove(self.Ticket.Ticket_ID == ticket_id)
        return True
    
    def flag_for_human_agent(self, ticket_id):
        """Flag a ticket as needing human assistance without moving it between tables"""
        # Check unresolved first, then resolved (though it should always be in unresolved)
        ticket = self.unresolved_table.get(self.Ticket.Ticket_ID == ticket_id)
        table = self.unresolved_table
        
        if not ticket:
            ticket = self.resolved_table.get(self.Ticket.Ticket_ID == ticket_id)
            table = self.resolved_table
            
        if not ticket:
            print(f"Ticket {ticket_id} not found")
            return False
        
        # Update ticket status to indicate it needs human assistance
        table.update({"Resolution_Status": "Needs Human Agent"}, self.Ticket.Ticket_ID == ticket_id)
        return True
    
    def get_ticket(self, ticket_id):
        """Get ticket data for a specific ticket ID"""
        # Check unresolved first, then resolved
        ticket = self.unresolved_table.get(self.Ticket.Ticket_ID == ticket_id)
        
        if not ticket:
            ticket = self.resolved_table.get(self.Ticket.Ticket_ID == ticket_id)
            
        return ticket
    
    def get_all_resolved_tickets(self):
        """Get all resolved tickets"""
        return self.resolved_table.all()
    
    def get_all_unresolved_tickets(self):
        """Get all unresolved tickets"""
        return self.unresolved_table.all()
    
    def search_tickets(self, query_text, include_resolved=True, include_unresolved=True):
        """Search tickets based on text"""
        results = []
        
        # Function to check if query text appears in ticket data
        def contains_query(ticket):
            if query_text.lower() in ticket.get('Issue_Category', '').lower():
                return True
            if query_text.lower() in ticket.get('Solution', '').lower():
                return True
            # Check conversation
            for msg in ticket.get('conversation', []):
                if query_text.lower() in msg.get('content', '').lower():
                    return True
            return False
        
        # Search in unresolved tickets
        if include_unresolved:
            for ticket in self.unresolved_table.all():
                if contains_query(ticket):
                    results.append(ticket)
        
        # Search in resolved tickets
        if include_resolved:
            for ticket in self.resolved_table.all():
                if contains_query(ticket):
                    results.append(ticket)
        
        return results

# Example usage:
if __name__ == "__main__":
    # Initialize ticketing system
    ticket_system = DynamicTicketing()
    
    # Create a new ticket
    ticket_id = ticket_system.create_new_ticket(
        issue_summary="App keeps crashing on startup",
        sentiment="Frustrated", 
        priority="High",
        assigned_team="Software"
    )
    
    # Add conversation
    ticket_system.update_conversation(ticket_id, "My app keeps crashing every time I try to open it.", "user")
    ticket_system.update_conversation(ticket_id, "I'm sorry to hear that. Have you tried reinstalling the app?", "assistant")
    ticket_system.update_conversation(ticket_id, "Yes, I tried that but it's still happening.", "user")
    
    # Mark as resolved
    ticket_system.mark_as_resolved(ticket_id, "Clear app cache and reinstall")
    
    # Get all unresolved tickets
    unresolved = ticket_system.get_all_unresolved_tickets()
    print(f"Unresolved tickets: {len(unresolved)}")
    
    # Get all resolved tickets
    resolved = ticket_system.get_all_resolved_tickets()
    print(f"Resolved tickets: {len(resolved)}") 