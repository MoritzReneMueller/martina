import os
import streamlit as st
import pandas as pd
import openai
from dotenv import load_dotenv
from crm_logic import CRMAgent

# Load environment variables
load_dotenv()

class AIAssistant:
    def __init__(self, api_key: str):
        openai.api_key = api_key
    
    def chat_with_martina(self, message: str, data: pd.DataFrame, conversation_history: list) -> str:
        try:
            conversation = [
                {"role": "system", "content": "You are Martina, a friendly and conversational CRM assistant. "
                 "Your goal is to help users manage their CRM data effectively. "
                 "You can assist with analyzing records and providing insights. "
                 "When users ask you to make changes, inform them to use the menu on the left."}
            ]
            
            conversation.extend([
                {"role": "user", "content": msg["user"]} if i % 2 == 0 else 
                {"role": "assistant", "content": msg["martina"]}
                for i, msg in enumerate(conversation_history)
            ])
            
            conversation.append({"role": "user", "content": message})
            
            crm_context = f"""
            Current CRM Data Overview:
            - Total Customers: {len(data)}
            - Columns: {', '.join(data.columns)}
            
            Sample Data:
            {data.head().to_string(index=False)}
            """
            conversation.insert(1, {"role": "system", "content": crm_context})
            
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=conversation,
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except openai.OpenAIError as e:
            error_message = f"OpenAI API Error: {str(e)}"
            st.error(error_message)
            return error_message
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            st.error(error_message)
            return error_message

def main():
    st.set_page_config(page_title="CRM Chatbot Martina", page_icon=":robot_face:", layout="wide")
    
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    
    file_path = "data.csv"
    
    st.title("🤖 CRM Chatbot Martina")
    st.markdown("Your AI-powered Customer Relationship Management Assistant")
    
    try:
        data = CRMAgent.load_data(file_path)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        data = pd.DataFrame(columns=["Customer ID", "First Name", "Last Name", "Email", "Phone", "Status", "Amount"])
    
    try:
        api_key = st.secrets.OPENAI_API_KEY
        if not api_key:
            st.error("OpenAI API Key not found in secrets")
            return
        assistant = AIAssistant(api_key)
    except Exception as e:
        st.error("Error initializing AI Assistant. Please check your API key configuration.")
        return
    
    with st.sidebar:
        st.header("CRM Actions")
        action = st.selectbox("Choose an Action", [
            "Chat with Martina", 
            "View All Customers", 
            "Add Customer", 
            "Update Customer",
            "Delete Customer",
            "Search Customers"
        ])
    
    if action == "Chat with Martina":
        st.subheader("💬 Chat with Martina")
        st.info("ℹ️ Martina can only analyse and retrieve records for now. To edit the database, use the menu on the left.")
        
        for msg in st.session_state["conversation_history"]:
            st.chat_message("user").write(msg['user'])
            st.chat_message("assistant").write(msg['martina'])
        
        if user_input := st.chat_input("Type your message"):
            try:
                bot_response = assistant.chat_with_martina(
                    user_input, 
                    data, 
                    st.session_state["conversation_history"]
                )
                
                st.session_state["conversation_history"].append({
                    "user": user_input,
                    "martina": bot_response
                })
                
                st.chat_message("user").write(user_input)
                st.chat_message("assistant").write(bot_response)
                
                data = CRMAgent.load_data(file_path)
                
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
    
    elif action == "View All Customers":
        st.subheader("📋 All Customers")
        if not data.empty:
            st.dataframe(data)
        else:
            st.info("No customers in the database yet.")
    
    elif action == "Add Customer":
        st.subheader("➕ Add New Customer")
        with st.form("add_customer_form"):
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            status = st.selectbox("Status", ["Prospect", "Active", "Inactive"])
            amount = st.number_input("Amount", min_value=0.0)
            
            submit_button = st.form_submit_button("Add Customer")
            
            if submit_button:
                customer_details = {
                    "First Name": first_name,
                    "Last Name": last_name,
                    "Email": email,
                    "Phone": phone,
                    "Status": status,
                    "Amount": amount
                }
                
                try:
                    result = CRMAgent.add_customer(data, customer_details, file_path)
                    st.success(result)
                    data = CRMAgent.load_data(file_path)
                except Exception as e:
                    st.error(f"Error adding customer: {e}")
    
    elif action == "Update Customer":
        st.subheader("✏️ Update Customer")
        if not data.empty:
            # Search functionality
            search_query = st.text_input("🔍 Search customers")
            
            # Create display DataFrame
            display_data = data.copy()
            display_data['Select'] = False
            
            # Filter data based on search
            if search_query:
                filtered_mask = display_data.astype(str).apply(
                    lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
                display_data = display_data[filtered_mask]
            
            # Create a streamlit data editor for selection
            edited_df = st.data_editor(
                display_data,
                hide_index=True,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select customer to edit",
                        default=False
                    )
                },
                disabled=display_data.columns.difference(['Select']).tolist()
            )
            
            # Get selected customer
            selected_rows = edited_df[edited_df['Select']]
            
            if len(selected_rows) > 1:
                st.warning("Please select only one customer to edit.")
            elif len(selected_rows) == 1:
                st.divider()
                st.subheader("Edit Customer Details")
                
                # Get current customer details
                current_customer = selected_rows.iloc[0]
                
                with st.form("update_customer_form"):
                    first_name = st.text_input("First Name", value=current_customer["First Name"])
                    last_name = st.text_input("Last Name", value=current_customer["Last Name"])
                    email = st.text_input("Email", value=current_customer["Email"])
                    phone = st.text_input("Phone", value=current_customer["Phone"])
                    status = st.selectbox(
                        "Status", 
                        ["Prospect", "Active", "Inactive"],
                        index=["Prospect", "Active", "Inactive"].index(current_customer["Status"])
                    )
                    amount = st.number_input(
                        "Amount", 
                        min_value=0.0, 
                        value=float(current_customer["Amount"])
                    )
                    
                    submit_button = st.form_submit_button("Update Customer")
                    
                    if submit_button:
                        updates = {
                            "First Name": first_name,
                            "Last Name": last_name,
                            "Email": email,
                            "Phone": phone,
                            "Status": status,
                            "Amount": amount
                        }
                        
                        try:
                            result = CRMAgent.update_customer(
                                data, 
                                current_customer["Customer ID"], 
                                updates, 
                                file_path
                            )
                            st.success(result)
                            data = CRMAgent.load_data(file_path)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating customer: {e}")
        else:
            st.info("No customers in the database yet.")
    
    elif action == "Delete Customer":
        st.subheader("🗑️ Delete Customer")
        if not data.empty:
            # Search functionality
            search_query = st.text_input("🔍 Search customers to delete")
            
            # Create display DataFrame
            display_data = data.copy()
            display_data['Select'] = False
            
            # Filter data based on search
            if search_query:
                filtered_mask = display_data.astype(str).apply(
                    lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
                display_data = display_data[filtered_mask]
            
            # Create a streamlit data editor for selection
            edited_df = st.data_editor(
                display_data,
                hide_index=True,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select customers to delete",
                        default=False
                    )
                },
                disabled=display_data.columns.difference(['Select']).tolist()
            )
            
            # Get selected customers
            selected_rows = edited_df[edited_df['Select']]
            
            if len(selected_rows) > 0:
                delete_button = st.button(
                    f"Delete {len(selected_rows)} selected customer{'s' if len(selected_rows) > 1 else ''}"
                )
                
                if delete_button:
                    try:
                        for _, customer in selected_rows.iterrows():
                            result = CRMAgent.delete_customer(data, customer["Customer ID"], file_path)
                            st.success(result)
                            # Reload data after each deletion
                            data = CRMAgent.load_data(file_path)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting customers: {e}")
        else:
            st.info("No customers in the database yet.")
    
    elif action == "Search Customers":
        st.subheader("🔍 Search Customers")
        search_query = st.text_input("Enter search term")
        
        if search_query:
            results = CRMAgent.search_records(data, search_query)
            
            if not results.empty:
                st.dataframe(results)
            else:
                st.info("No customers found matching the search term.")

if __name__ == "__main__":
    main()
