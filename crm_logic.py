import pandas as pd
from typing import Dict, Any, Optional
import streamlit as st
import os

class CRMAgent:
    @staticmethod
    def load_data(file_path: str = "data.csv") -> pd.DataFrame:
        """
        Load CRM data from CSV file with robust error handling and column management
        """
        # Define required columns at the start
        required_columns = {
            "Customer ID": "Int64",
            "First Name": "object",
            "Last Name": "object",
            "Email": "object", 
            "Phone": "object", 
            "Status": "object", 
            "Amount": "float64"
        }
        
        try:
            # Check if file path is provided
            if not file_path:
                file_path = "data.csv"
                
            # Read CSV file if it exists
            if os.path.exists(file_path):
                data = pd.read_csv(file_path, delimiter=';')
                
                # Drop unnecessary columns
                data = data.drop(columns=[col for col in data.columns if 'Unnamed:' in col], errors='ignore')
                
                # Handle legacy data with Name field
                if 'Name' in data.columns:
                    if 'First Name' not in data.columns or 'Last Name' not in data.columns:
                        # Split existing names into First Name and Last Name
                        name_parts = data['Name'].str.split(' ', n=1)
                        data['First Name'] = name_parts.str[0]
                        data['Last Name'] = name_parts.str[1].fillna('')  # Handle single names
                    # Remove the Name column
                    data = data.drop(columns=['Name'])
            else:
                data = pd.DataFrame(columns=list(required_columns.keys()))
            
            # Ensure all expected columns are present with correct types
            for column, dtype in required_columns.items():
                if column not in data.columns:
                    data[column] = pd.Series(dtype=dtype)
                else:
                    try:
                        data[column] = data[column].astype(dtype)
                    except Exception:
                        data[column] = pd.Series(dtype=dtype)
            
            # Remove completely empty rows and reset index
            data = data.dropna(how="all").reset_index(drop=True)
            
            return data
            
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame(columns=list(required_columns.keys()))

    @staticmethod
    def save_data(df: pd.DataFrame, file_path: str = "data.csv") -> None:
        """
        Save DataFrame to CSV file
        """
        try:
            df.to_csv(file_path, index=False, sep=';')
            st.success(f"Data successfully saved to {file_path}")
        except Exception as e:
            st.error(f"Error saving data to {file_path}: {e}")
            raise

    @staticmethod
    def add_customer(data: pd.DataFrame, customer_details: Dict[str, Any], file_path: str = "data.csv") -> str:
        """
        Add a new customer to the CRM
        """
        try:
            # Validate input data
            required_fields = ["First Name", "Last Name", "Email", "Phone", "Status", "Amount"]
            for field in required_fields:
                if field not in customer_details or not customer_details[field]:
                    return f"Error: {field} is required"
            
            # Auto-increment Customer ID
            new_id = 1
            if not data.empty and 'Customer ID' in data.columns:
                new_id = int(data['Customer ID'].max() + 1)
            
            # Add Customer ID to the details
            customer_details["Customer ID"] = new_id
            
            # Create new customer record
            new_record = pd.DataFrame([customer_details])
            
            # Combine existing data with new record
            updated_data = pd.concat([data, new_record], ignore_index=True)
            
            # Save updated data
            CRMAgent.save_data(updated_data, file_path)
            
            return f"Customer added successfully with ID {new_id}"
            
        except Exception as e:
            return f"Error adding customer: {str(e)}"

    @staticmethod
    def update_customer(data: pd.DataFrame, customer_id: int, updates: Dict[str, Any], file_path: str = "data.csv") -> str:
        """
        Update an existing customer record
        """
        try:
            # Find the customer
            customer_mask = data['Customer ID'] == customer_id
            
            if not any(customer_mask):
                return f"No customer found with ID {customer_id}"
            
            # Update the record
            for key, value in updates.items():
                if key in data.columns:
                    data.loc[customer_mask, key] = value
            
            # Save updated data
            CRMAgent.save_data(data, file_path)
            return f"Customer with ID {customer_id} updated successfully"
            
        except Exception as e:
            return f"Error updating customer: {str(e)}"

    @staticmethod
    def search_records(data: pd.DataFrame, query: str) -> pd.DataFrame:
        """
        Search for customers based on a query
        """
        query = query.lower()
        return data[data.astype(str).apply(lambda x: x.str.lower()).apply(
            lambda x: x.str.contains(query, na=False)).any(axis=1)]

    @staticmethod
    def delete_customer(data: pd.DataFrame, customer_id: int, file_path: str = "data.csv") -> str:
        """
        Delete a customer by ID
        """
        try:
            if customer_id not in data['Customer ID'].values:
                return f"No customer found with ID {customer_id}"
            
            # Remove the customer
            updated_data = data[data['Customer ID'] != customer_id]
            
            # Save updated data
            CRMAgent.save_data(updated_data, file_path)
            return f"Customer with ID {customer_id} deleted successfully"
            
        except Exception as e:
            return f"Error deleting customer: {str(e)}"