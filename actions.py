from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, ActiveLoop, FollowupAction

# 💡 Helper function to simulate checking if a station name is valid
def is_valid_station(station_name: Text) -> bool:
    # In a real-world scenario, you would check a database of station codes.
    # Here, we'll just check if the name is reasonably long.
    return len(station_name) > 3

class ValidateTicketBookingForm(FormValidationAction):
    def name(self) -> Text:
        # This name must match the form name in your domain.yml
        return "validate_ticket_booking_form"

    def validate_source(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validate source value."""
        if is_valid_station(slot_value):
            # Validation succeeded, keep the value
            return {"source": slot_value}
        else:
            # Validation failed, set slot to None and ask again
            dispatcher.utter_message(text=f"I don't recognize '{slot_value}' as a valid source station. Could you please specify a major station name?")
            return {"source": None}

    def validate_destination(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validate destination value."""
        if is_valid_station(slot_value):
            # Validation succeeded, keep the value
            source = tracker.get_slot("source")
            if source and source.lower() == slot_value.lower():
                # Destination cannot be the same as source
                dispatcher.utter_message(text="Source and Destination stations cannot be the same. Please specify a different destination.")
                return {"destination": None}
            # Validation succeeded
            return {"destination": slot_value}
        else:
            # Validation failed
            dispatcher.utter_message(text=f"I don't recognize '{slot_value}' as a valid destination station. Please try another name.")
            return {"destination": None}
            
    def validate_payment_method(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validate payment method."""
        supported_methods = ["upi", "card", "credit card", "debit card", "net banking", "google pay"]
        
        # Simple check for keywords in the user input
        if any(method in slot_value.lower() for method in supported_methods):
            # Validation succeeded, store the normalized method
            return {"payment_method": slot_value}
        else:
            # Validation failed
            dispatcher.utter_message(text="I'm sorry, we only support **UPI, Credit/Debit Card, or Net Banking**. Please choose one of these.")
            return {"payment_method": None}

class ActionConfirmPayment(Action):
    def name(self) -> Text:
        return "action_confirm_payment"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        source = tracker.get_slot("source")
        destination = tracker.get_slot("destination")
        payment_method = tracker.get_slot("payment_method")
        
        # Simulate ticket price (e.g., based on distance, time, etc.)
        # For simplicity, we use a fixed price.
        TICKET_PRICE = 120 

        # Construct the confirmation message
        message = (
            f"Please confirm your booking details:\n\n"
            f"**Route:** {source} to {destination}\n"
            f"**Amount:** Rs {TICKET_PRICE}\n"
            f"**Payment Method:** {payment_method}\n\n"
            "Do you want to **confirm and proceed** with the payment?"
        )
        
        dispatcher.utter_message(text=message)
        
        # Set a temporary slot to track that we are waiting for confirmation
        # The 'action_process_booking' will check the next user intent (affirm/deny)
        return [SlotSet("payment_confirmed", None)] # Clear previous confirmation status
    
import random
from datetime import datetime, timedelta
# ... (Keep the existing imports from the previous action code)

# 💡 A simple database simulation (store in a dictionary)
# In a real app, this would be a SQL database or a secure backend.
TICKET_DB = {} 

class ActionProcessBooking(Action):
    def name(self) -> Text:
        return "action_process_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        # Check if the user's last intent was 'affirm' after confirmation
        if tracker.latest_message.get("intent", {}).get("name") == "affirm":
            
            source = tracker.get_slot("source")
            destination = tracker.get_slot("destination")
            payment_method = tracker.get_slot("payment_method")
            
            # --- 1. Simulate API/Database Call ---
            pnr_number = str(random.randint(1000000000, 9999999999))
            booking_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # The "user_id" could be the sender_id in a real system
            user_id = tracker.sender_id 
            
            # Store the simulated ticket
            if user_id not in TICKET_DB:
                TICKET_DB[user_id] = []
                
            TICKET_DB[user_id].append({
                "pnr": pnr_number,
                "source": source,
                "destination": destination,
                "payment": payment_method,
                "booked_on": booking_time,
                "status": "CONFIRMED"
            })
            
            # --- 2. Send Success Message ---
            message = (
                f"**Booking Successful!** Your reserved ticket is confirmed.\n\n"
                f"**PNR:** {pnr_number}\n"
                f"**Route:** {source} to {destination}\n"
                f"**Payment Method:** {payment_method}\n"
            )
            dispatcher.utter_message(text=message)
            
            # Reset the slots for a new booking
            return [
                SlotSet("source", None),
                SlotSet("destination", None),
                SlotSet("payment_method", None),
                SlotSet("payment_confirmed", None),
            ]
            
        else: # User denied the confirmation
            dispatcher.utter_message(text="Ticket booking cancelled. Is there anything else I can help you with?")
            # Reset the slots for a new booking
            return [
                SlotSet("source", None),
                SlotSet("destination", None),
                SlotSet("payment_method", None),
                SlotSet("payment_confirmed", None),
            ]

class ActionRetrieveTickets(Action):
    def name(self) -> Text:
        return "action_retrieve_tickets"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        user_id = tracker.sender_id
        user_tickets = TICKET_DB.get(user_id, [])
        
        if not user_tickets:
            # No tickets found
            dispatcher.utter_message(text="You currently have no unreserved tickets booked with me.")
            return []

        # --- Format and display the tickets ---
        
        # Sort by most recent booking first
        user_tickets.sort(key=lambda x: x["booked_on"], reverse=True)
        
        message_parts = ["Here are your recent unreserved ticket bookings:"]
        
        for i, ticket in enumerate(user_tickets):
            message_parts.append(
                f"\n--- Ticket {i+1} ---\n"
                f"**PNR:** {ticket['pnr']}\n"
                f"**Route:** {ticket['source']} to {ticket['destination']}\n"
                f"**Booked On:** {ticket['booked_on'].split(' ')[0]}" # Just show date
            )
            
        final_message = "\n".join(message_parts)
        dispatcher.utter_message(text=final_message)

        return []