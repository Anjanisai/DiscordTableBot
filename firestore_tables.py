from firebase_setup import db
from typing import List, Dict, Any, Optional
import logging
from google.cloud import firestore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_table(server_id: str, table_name: str, columns: List[str], rows: List[List[Any]]) -> bool:
    """Save or update a table in Firestore with error handling"""
    try:
        # Convert rows to list of dictionaries to avoid nested arrays
        rows_as_dicts = [dict(zip(columns, row)) for row in rows]
        
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        table_ref.set({
            "columns": columns,
            "rows": rows_as_dicts  # Store rows as dictionaries
        })
        logger.info(f"Table '{table_name}' saved for server {server_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving table {table_name}: {str(e)}")
        return False

def get_table(server_id: str, table_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a table from Firestore with error handling"""
    try:
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        doc = table_ref.get()
        if doc.exists:
            data = doc.to_dict()
            # Convert rows back to list of lists if needed
            if data and 'rows' in data and all(isinstance(row, dict) for row in data['rows']):
                data['rows'] = [list(row.values()) for row in data['rows']]
            return data
        return None
    except Exception as e:
        logger.error(f"Error getting table {table_name}: {str(e)}")
        return None

def add_table_row(server_id: str, table_name: str, new_row: List[Any]) -> bool:
    """Specialized function to safely add a row to a table"""
    try:
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        doc = table_ref.get()
        
        if not doc.exists:
            return False
            
        data = doc.to_dict()
        columns = data.get("columns", [])
        
        if len(new_row) != len(columns):
            return False
            
        # Convert the new row to a dictionary
        new_row_dict = dict(zip(columns, new_row))
        
        # Update the document
        table_ref.update({
            "rows": firestore.ArrayUnion([new_row_dict])
        })
        logger.info(f"Added row to {table_name} in server {server_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding row to {table_name}: {str(e)}")
        return False

def delete_table(server_id: str, table_name: str) -> bool:
    """Delete a table from Firestore"""
    try:
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        table_ref.delete()
        logger.info(f"🗑️ Table '{table_name}' deleted for server {server_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting table {table_name}: {str(e)}")
        return False

def get_guild_tables(server_id: str) -> Dict[str, Dict[str, Any]]:
    """Get all tables for a specific server"""
    try:
        tables_ref = db.collection("servers").document(str(server_id)).collection("tables")
        docs = tables_ref.stream()
        result = {}
        for doc in docs:
            data = doc.to_dict()
            # Convert rows back to list of lists if needed
            if data and 'rows' in data and all(isinstance(row, dict) for row in data['rows']):
                data['rows'] = [list(row.values()) for row in data['rows']]
            result[doc.id] = data
        return result
    except Exception as e:
        logger.error(f"Error getting tables for server {server_id}: {str(e)}")
        return {}

def table_exists(server_id: str, table_name: str) -> bool:
    """Check if a table exists"""
    try:
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        doc = table_ref.get()
        return doc.exists
    except Exception as e:
        logger.error(f"Error checking table existence {table_name}: {str(e)}")
        return False

def update_table_columns(server_id: str, table_name: str, columns: List[str]) -> bool:
    """Update only the columns of a table"""
    try:
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        table_ref.update({"columns": columns})
        logger.info(f"Updated columns for table {table_name}")
        return True
    except Exception as e:
        logger.error(f"Error updating columns for table {table_name}: {str(e)}")
        return False

def update_table_rows(server_id: str, table_name: str, rows: List[List[Any]]) -> bool:
    """Update only the rows of a table"""
    try:
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        doc = table_ref.get()
        
        if not doc.exists:
            return False
            
        data = doc.to_dict()
        columns = data.get("columns", [])
        
        # Convert rows to dictionaries
        rows_as_dicts = [dict(zip(columns, row)) for row in rows]
        
        table_ref.update({"rows": rows_as_dicts})
        logger.info(f"Updated rows for table {table_name}")
        return True
    except Exception as e:
        logger.error(f"Error updating rows for table {table_name}: {str(e)}")
        return False

def clear_table_rows(server_id: str, table_name: str) -> bool:
    """Clear all rows from a table while keeping columns"""
    try:
        table_ref = db.collection("servers").document(str(server_id)).collection("tables").document(table_name)
        table_ref.update({"rows": []})
        logger.info(f"Cleared rows for table {table_name}")
        return True
    except Exception as e:
        logger.error(f"Error clearing rows for table {table_name}: {str(e)}")
        return False

def get_table_size(server_id: str, table_name: str) -> Dict[str, int]:
    """Get the dimensions of a table (columns count and rows count)"""
    try:
        table_data = get_table(server_id, table_name)
        if not table_data:
            return {"columns": 0, "rows": 0}
        return {
            "columns": len(table_data.get("columns", [])),
            "rows": len(table_data.get("rows", []))
        }
    except Exception as e:
        logger.error(f"Error getting table size for {table_name}: {str(e)}")
        return {"columns": 0, "rows": 0}