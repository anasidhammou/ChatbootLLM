import sqlite3
import uuid
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional, List, Dict, Any
from chatbot.models import Account
from chatbot.config import DB_FILE, DB_INIT_SQL


def auth_user(user_id: str, password: str) -> bool:
    """
    Ensure the user id and password are match to pair stored in database.  This is a just a part of a simple demo, you should never store clear text passwords in production.

    :param user_id: The user ID that needing authentcation.
    :param password: The matching password to the user ID.
    :return: True if user ID and password are matched, False otherwise.
    """
    sql = "SELECT UserId FROM UserCredentials WHERE UserId=:user_id AND Password=:password"
    con = sqlite3.connect('bank.db')
    cur = con.cursor()
    cur.execute(sql, {"user_id": user_id, "password": password})
    authenticated = cur.fetchone() is not None
    con.close()
    return authenticated


def load_accounts() -> list[Account]:
    """
    Query all accounts from the database.

    :return: All the accounts in the database
    """
    print(f"he is here")

    sql = "SELECT AccountNumber, AccountName, Balance FROM Accounts"
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    accounts = []
    for row in rows:
        account = Account()
        account.account_number = row['AccountNumber']
        account.account_name = row['AccountName']
        account.balance = Decimal(str(row['Balance']))
        accounts.append(account)
    con.close()
    return accounts


def load_transfer_target_accounts(from_account: str) -> list[Account]:
    """
    Query accounts that the specified account can transfer fund to.

    :param from_account: The account number or account name that the fund would be transferred from.
    :return: All the accounts that the specified account can transfer to (excluding the source account).
    """
    sql = """
    SELECT AccountNumber, AccountName, Balance 
    FROM Accounts 
    WHERE AccountNumber != :from_account
    """
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, {"from_account": from_account})
    rows = cur.fetchall()
    accounts = []
    for row in rows:
        account = Account()
        account.account_number = row['AccountNumber']
        account.account_name = row['AccountName']
        account.balance = Decimal(str(row['Balance']))
        accounts.append(account)
    con.close()
    return accounts


def transfer_fund_between_accounts(user_id: str,
                                   from_account: str, to_account: str,
                                   amount: Decimal):
    """
    Deduct fund from one account then add to the other account all under the same owner
    
    :param user_id: The user ID of the account owner
    :param from_account: The account number or account name that the fund would be transferred from.
    :param to_account: The account number or account name that the fund would be transferred to.
    :param amount: The amount that is going to be transfered.
    """
    # Debug the parameters
    print(f"[DEBUG] transfer_fund_between_accounts: user_id={user_id}, from={from_account}, to={to_account}, amount={amount} (type: {type(amount)})")
    
    # Ensure amount is a Decimal
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    
    try:
        # Start a transaction
        con.execute("BEGIN TRANSACTION")
        
        # Convert amount to string for SQLite
        amount_str = str(amount)
        
        # Deduct from source account
        cur.execute(
            "UPDATE Accounts SET Balance = Balance - ? WHERE  AccountNumber=?",
            (amount_str, user_id, from_account)
        )
        
        # Add to destination account
        cur.execute(
            "UPDATE Accounts SET Balance = Balance + ? WHERE AccountNumber=?",
            (amount_str, user_id, to_account)
        )
        
        # Get the updated balances after the transfer
        cur.execute("SELECT Balance FROM Accounts WHERE  AccountNumber=?", 
                   (user_id, from_account))
        from_account_balance = cur.fetchone()[0]
        
        cur.execute("SELECT Balance FROM Accounts WHERE  AccountNumber=?", 
                   (user_id, to_account))
        to_account_balance = cur.fetchone()[0]
        
        # Record the transfer with balances
        import uuid
        import datetime
        transaction_id = str(uuid.uuid4())
        current_time = datetime.datetime.now().isoformat()
        
        cur.execute(
            """
            INSERT INTO Transfers (
                TransactionNumber, FromAccountNumber, ToAccountNumber, 
                TransferDateTime, Amount, FromAccountBalance, ToAccountBalance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (transaction_id, from_account, to_account, current_time, 
             amount_str, from_account_balance, to_account_balance)
        )
        
        # Commit the transaction
        con.commit()
        print(f"[DEBUG] Transfer successful: {amount_str} from {from_account} to {to_account}")
    except Exception as e:
        # Rollback in case of error
        con.rollback()
        print(f"[ERROR] Database error during transfer: {str(e)}")
        raise e
    finally:
        con.close()


# === NOUVELLES FONCTIONS POUR LES REQUÊTES DE COMPTES ===

def get_account_by_number(account_number: str, user_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Récupère les informations d'un compte par son numéro.
    
    :param account_number: Le numéro du compte
    :param user_id: ID utilisateur (optionnel pour filtrage)
    :return: Dictionnaire avec les infos du compte ou None si non trouvé
    """
    if user_id:
        sql = "SELECT AccountNumber, AccountName, Balance FROM Accounts WHERE AccountNumber = ? AND UserId = ?"
        params = (account_number, user_id)
    else:
        sql = "SELECT AccountNumber, AccountName, Balance FROM Accounts WHERE AccountNumber = ?"
        params = (account_number,)
    
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    con.close()
    
    if row:
        return {
            'account_number': row['AccountNumber'],
            'account_name': row['AccountName'],
            'balance': Decimal(str(row['Balance']))
        }
    return None


def get_account_by_name(account_name: str, user_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Récupère les informations d'un compte par son nom.
    
    :param account_name: Le nom du compte (recherche partielle insensible à la casse)
    :param user_id: ID utilisateur (optionnel pour filtrage)
    :return: Dictionnaire avec les infos du compte ou None si non trouvé
    """
    if user_id:
        sql = "SELECT AccountNumber, AccountName, Balance FROM Accounts WHERE LOWER(AccountName) LIKE LOWER(?) AND UserId = ?"
        params = (f"%{account_name}%", user_id)
    else:
        sql = "SELECT AccountNumber, AccountName, Balance FROM Accounts WHERE LOWER(AccountName) LIKE LOWER(?)"
        params = (f"%{account_name}%",)
    
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    con.close()
    
    if row:
        return {
            'account_number': row['AccountNumber'],
            'account_name': row['AccountName'],
            'balance': Decimal(str(row['Balance']))
        }
    return None


def get_all_accounts_info(user_id: str = None) -> List[Dict[str, Any]]:
    """
    Récupère toutes les informations des comptes.
    
    :param user_id: ID utilisateur (optionnel pour filtrage)
    :return: Liste des dictionnaires avec les infos des comptes
    """
    if user_id:
        sql = "SELECT AccountNumber, AccountName, Balance FROM Accounts WHERE UserId = ? ORDER BY AccountName"
        params = (user_id,)
    else:
        sql = "SELECT AccountNumber, AccountName, Balance FROM Accounts ORDER BY AccountName"
        params = ()
    
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    
    accounts = []
    for row in rows:
        accounts.append({
            'account_number': row['AccountNumber'],
            'account_name': row['AccountName'],
            'balance': Decimal(str(row['Balance']))
        })
    return accounts


def get_account_transactions(account_number: str, user_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Récupère les dernières transactions d'un compte.
    
    :param account_number: Le numéro du compte
    :param user_id: ID utilisateur (optionnel pour filtrage)
    :param limit: Nombre maximum de transactions à retourner
    :return: Liste des transactions
    """
    # Vérifier d'abord que le compte appartient à l'utilisateur si user_id est fourni
    if user_id:
        account_check_sql = "SELECT 1 FROM Accounts WHERE AccountNumber = ? AND UserId = ?"
        con_check = sqlite3.connect(DB_FILE)
        cur_check = con_check.cursor()
        cur_check.execute(account_check_sql, (account_number, user_id))
        if not cur_check.fetchone():
            con_check.close()
            return []  # Compte non trouvé ou n'appartient pas à l'utilisateur
        con_check.close()
    
    sql = """
    SELECT 
        TransactionNumber,
        CASE 
            WHEN FromAccountNumber = ? THEN 'DEBIT'
            WHEN ToAccountNumber = ? THEN 'CREDIT'
        END as Type,
        CASE 
            WHEN FromAccountNumber = ? THEN ToAccountNumber
            WHEN ToAccountNumber = ? THEN FromAccountNumber
        END as OtherAccount,
        Amount,
        TransferDateTime,
        CASE 
            WHEN FromAccountNumber = ? THEN FromAccountBalance
            WHEN ToAccountNumber = ? THEN ToAccountBalance
        END as BalanceAfter
    FROM Transfers 
    WHERE FromAccountNumber = ? OR ToAccountNumber = ?
    ORDER BY TransferDateTime DESC
    LIMIT ?
    """
    
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, (account_number, account_number, account_number, 
                     account_number, account_number, account_number,
                     account_number, account_number, limit))
    rows = cur.fetchall()
    con.close()
    
    transactions = []
    for row in rows:
        transactions.append({
            'transaction_id': row['TransactionNumber'],
            'type': row['Type'],
            'other_account': row['OtherAccount'],
            'amount': Decimal(str(row['Amount'])),
            'date_time': row['TransferDateTime'],
            'balance_after': Decimal(str(row['BalanceAfter']))
        })
    
    return transactions

def get_total_balance(user_id: str = None) -> Decimal:
    """
    Calcule le solde total de tous les comptes.
    
    :param user_id: ID utilisateur (optionnel pour filtrage)
    :return: Solde total
    """
    if user_id:
        sql = "SELECT SUM(Balance) as TotalBalance FROM Accounts WHERE UserId = ?"
        params = (user_id,)
    else:
        sql = "SELECT SUM(Balance) as TotalBalance FROM Accounts"
        params = ()
    
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(sql, params)
    result = cur.fetchone()
    con.close()
    
    return Decimal(str(result[0])) if result[0] else Decimal('0.00')


def search_accounts(query: str) -> List[Dict[str, Any]]:
    """
    Recherche des comptes par numéro ou nom.
    
    :param query: Terme de recherche
    :return: Liste des comptes correspondants
    """
    sql = """
    SELECT AccountNumber, AccountName, Balance 
    FROM Accounts 
    WHERE AccountNumber LIKE ? OR LOWER(AccountName) LIKE LOWER(?)
    ORDER BY AccountName
    """
    
    search_term = f"%{query}%"
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, (search_term, search_term))
    rows = cur.fetchall()
    con.close()
    
    accounts = []
    for row in rows:
        accounts.append({
            'account_number': row['AccountNumber'],
            'account_name': row['AccountName'],
            'balance': Decimal(str(row['Balance']))
        })
    return accounts


def get_account_balance(account_identifier: str) -> Optional[Decimal]:
    """
    Récupère le solde d'un compte par numéro ou nom.
    
    :param account_identifier: Numéro ou nom du compte
    :return: Solde du compte ou None si non trouvé
    """
    # D'abord essayer par numéro de compte
    account = get_account_by_number(account_identifier)
    if not account:
        # Ensuite essayer par nom
        account = get_account_by_name(account_identifier)
    
    return account['balance'] if account else None


def get_total_balance() -> Decimal:
    """
    Calcule le solde total de tous les comptes.
    
    :return: Solde total
    """
    sql = "SELECT SUM(Balance) as TotalBalance FROM Accounts"
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(sql)
    result = cur.fetchone()
    con.close()
    
    return Decimal(str(result[0])) if result[0] else Decimal('0.00')


def init_db():
    """
    Create the database and add inital test data.
    """
    # Check if database file already exists and has tables
    db_exists = Path(DB_FILE).exists()
    
    if db_exists:
        # Check if tables already exist
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='UserCredentials'")
        table_exists = cur.fetchone() is not None
        con.close()
        
        if table_exists:
            print(f"Database {DB_FILE} already initialized.")
            return
    
    # Create and initialize the database
    with open(DB_INIT_SQL) as sql_file:
        sql = sql_file.read()
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.executescript(sql)
        con.commit()
        con.close()
        print(f"Database {DB_FILE} initialized successfully.")