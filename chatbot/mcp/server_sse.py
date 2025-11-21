from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from decimal import Decimal
import os
import sys
import datetime

# Add the parent directory to the Python path to import from src and chatbot
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(parent_dir)
print(f"Added to Python path: {parent_dir}")

# Import RAG components
from chatbot.rag.rag_chatbot import S2MChatbot

# Import the actual database functions
from chatbot.account import list_accounts, list_transfer_target_accounts, transfer_between_accounts
from chatbot.database import init_db
from chatbot.models import Account

# Import Account Query Handler and Intent Detector
from chatbot.account_query_handler import AccountQueryHandler
from chatbot.intent_detector import IntentDetector

# Load environment variables from .env file
load_dotenv("../../.env")

# Initialize the database if it doesn't exist (will check internally)
init_db()

# Initialize the RAG chatbot
chatbot = S2MChatbot()

# Initialize the Account Query Handler
account_handler = AccountQueryHandler()
intent_detector = IntentDetector()

# Import configuration
from chatbot.config import MCP_NAME, MCP_HOST, MCP_PORT, DEFAULT_USER_ID

# Create the MCP server
mcp = FastMCP(name=MCP_NAME, host=MCP_HOST, port=MCP_PORT)

# NEW TOOL: Account Query Handler - Handle natural language banking questions
@mcp.tool()
def handle_banking_query(user_message: str, user_id: str = DEFAULT_USER_ID) -> dict:
    """
    Handle natural language banking queries about accounts, balances, transactions, etc.
    This tool processes questions like:
    - "What's my account balance?"
    - "Show me all my accounts"
    - "Transaction history for my savings account"
    - "How much money do I have in total?"
    
    Args:
        user_message: The user's natural language question about their banking accounts
        user_id: The user ID for filtering account access (defaults to DEFAULT_USER_ID)
    
    Returns:
        Dictionary with response and query type information
    """
    print(f"[BANKING_QUERY] Processing: {user_message}")
    
    # First check if it's a system command
    command, arg = intent_detector.detect_command(user_message)
    if command:
        print(f"[BANKING_QUERY] System command detected: {command}")
        return {
            "response": f"System command '{command}' detected",
            "query_type": "system_command",
            "command": command,
            "argument": arg
        }
    
    # Check if it's a banking query
    if account_handler.is_banking_query(user_message):
        print(f"[BANKING_QUERY] Banking query detected")
        
        # Get the banking intent and extracted info
        intent, extracted_info = intent_detector.detect_banking_intent(user_message)
        
        # Handle the query
        response = account_handler.handle_query(user_message, user_id)
        
        return {
            "response": response,
            "query_type": "banking_query",
            "intent": intent,
            "extracted_info": extracted_info,
            "confidence": intent_detector.get_intent_confidence(user_message, intent) if intent else 0.0
        }
    else:
        print(f"[BANKING_QUERY] Not a banking query, suggest using RAG")
        return {
            "response": "Cette question ne semble pas concerner vos comptes bancaires. Utilisez l'outil RAG pour les questions générales sur les services bancaires.",
            "query_type": "non_banking",
            "suggestion": "use_rag_tool"
        }

# RAG Tool: Answer questions using the RAG system
@mcp.tool()
def answer_banking_question(question: str) -> dict:
    """
    Returns the answer and sources.
    """
    print(f"[RAG] Processing question: {question}")
    
    # Process the question - the model should determine if it's banking-related
    # based on the system instructions
    result = chatbot.answer_question(question)
    print(f"[RAG] Found answer with {len(result['sources'])} sources")
    return {
        "answer": result["answer"],
        "sources": result["sources"]
    }

# Tool 1: List all accounts belonging to a user
@mcp.tool()
def list_user_accounts(user_id: str) -> list[dict]:
    """List all accounts for a given user."""
    accounts = list_accounts()
    print(f"[DEBUG] list_user_accounts called")
    print(f"[DEBUG] Accounts: {accounts}")
    return [account.__dict__ for account in accounts]

# Tool 2: List target accounts that can receive transfers
@mcp.tool()
def list_target_accounts(user_id: str, from_account: str) -> list[dict]:
    """List all other accounts this user can transfer to."""
    accounts = list_transfer_target_accounts(user_id, from_account)
    print(f"[DEBUG] list_target_accounts called with user_id={user_id}, from_account={from_account}")
    print(f"[DEBUG] Transfer targets: {accounts}")
    return [account.__dict__ for account in accounts]

# Tool 3: Transfer funds between two accounts
@mcp.tool()
def transfer_funds(user_id: str, from_account: str, to_account: str, amount: str) -> str:
    """Transfer funds from one account to another."""
    print(f"[DEBUG] transfer_funds called with user_id={user_id}, from_account={from_account}, to_account={to_account}, amount={amount}")
    try:
        # Convert amount to Decimal, handling any formatting issues
        clean_amount = amount.replace('$', '').replace(',', '')
        decimal_amount = Decimal(clean_amount)
        
        # Debug the parameters
        print(f"[DEBUG] Parsed amount: {decimal_amount} (type: {type(decimal_amount)})")
        print(f"[DEBUG] from_account: {from_account} (type: {type(from_account)})")
        print(f"[DEBUG] to_account: {to_account} (type: {type(to_account)})")
        
        # Call the transfer function
        transfer_between_accounts(user_id, from_account, to_account, decimal_amount)
        return f"✅ Transferred MAD{clean_amount} from {from_account} to {to_account}."
    except Exception as e:
        print(f"[ERROR] Transfer failed: {str(e)}")
        return f"❌ Transfer failed: {str(e)}"

# Tool 4: Get account balance
@mcp.tool()
def get_account_balance(user_id: str, account_number: str) -> dict:
    """Get the balance of a specific account."""
    print(f'[DEBUG] get_account_balance called with user_id={user_id}, account_number={account_number}')
    
    # Find the account in the user's accounts
    accounts = list_accounts()
    for account in accounts:
        if account.account_number == account_number:
            return {
                "account_number": account.account_number,
                "account_name": account.account_name,
                "balance": str(account.balance),
                "currency": "MAD"
            }
    
    return {"error": f"Account {account_number} not found."}

# Tool 5: Get transaction history
@mcp.tool()
def get_transaction_history(user_id: str, account_number: str, days: int = 30) -> list[dict]:
    """Get the transaction history for a specific account."""
    print(f"[DEBUG] get_transaction_history called with user_id={user_id}, account_number={account_number}, days={days}")
    
    # Connect to the database to get transaction history
    import sqlite3
    from chatbot.database import DB_FILE
    
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    # Calculate the date range
    today = datetime.datetime.now()
    start_date = (today - datetime.timedelta(days=days)).isoformat()
    
    # Query for transactions with balances
    cur.execute("""
        SELECT 
            TransactionNumber, 
            TransferDateTime, 
            CASE 
                WHEN FromAccountNumber = :account_number THEN 'debit' 
                ELSE 'credit' 
            END as transaction_type,
            CASE 
                WHEN FromAccountNumber = :account_number THEN -Amount 
                ELSE Amount 
            END as amount,
            CASE 
                WHEN FromAccountNumber = :account_number THEN 'Transfer to ' || ToAccountNumber
                ELSE 'Transfer from ' || FromAccountNumber
            END as description,
            CASE 
                WHEN FromAccountNumber = :account_number THEN FromAccountBalance
                ELSE ToAccountBalance
            END as balance_after
        FROM Transfers
        WHERE (FromAccountNumber = :account_number OR ToAccountNumber = :account_number)
        AND TransferDateTime >= :start_date
        ORDER BY TransferDateTime DESC
    """, {"account_number": account_number, "start_date": start_date})
    
    rows = cur.fetchall()
    
    # Create transaction objects using stored balances
    transactions = []
    
    for row in rows:
        amount = Decimal(str(row['amount']))
        
        transaction = {
            "transaction_id": row['TransactionNumber'],
            "date": row['TransferDateTime'].split('T')[0],  # Just the date part
            "description": row['description'],
            "amount": str(amount),
            "transaction_type": row['transaction_type'],
            "balance_after": str(row['balance_after'])
        }
        transactions.append(transaction)
    
    con.close()
    print(f"[DEBUG] Returning: {len(transactions)} transactions")
    return transactions

# Run the MCP server using SSE transport
if __name__ == "__main__":
    print("[INFO] Starting MCP server on http://127.0.0.1:8050 using SSE transport...")
    mcp.run(transport="sse")