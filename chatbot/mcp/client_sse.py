"""Interactive Banking Agent using OpenAI and MCP - Version Modifiée."""
import os
import asyncio
import sys
import json
import random
from typing import Dict, List, Any, Optional, Tuple

# Add the parent directory to the Python path to import from src and chatbot
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Import custom modules
from chatbot.config import DEFAULT_USER_ID, ACCOUNT_MAPPINGS
from chatbot.config_client import (
    SYSTEM_INSTRUCTIONS, 
    TOOL_DEFINITIONS, MODEL_CONFIG
)
from chatbot.response_formatter import ResponseFormatter
from chatbot.intent_detector import IntentDetector

# Load environment variables
load_dotenv("../../.env")

class InteractiveBankingAssistant:
    """Interactive banking agent using OpenAI and MCP."""
    
    def __init__(self):
        """Initialize the banking assistant."""
        self.conversation_history = []
        self.user_id = DEFAULT_USER_ID
        self.session = None
        self.read_stream = None
        self.write_stream = None
        self.account_mappings = ACCOUNT_MAPPINGS
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key="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"
        )
        
        # Initialize a separate OpenAI client for general questions
        self.general_openai_client = AsyncOpenAI(
            api_key="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"
        )
    
    def _is_banking_related(self, question):
        """Check if a question is related to banking/finance"""
        banking_keywords = [
            'bank', 'banking', 'account', 'loan', 'credit', 'mortgage', 'investment',
            'savings', 'checking', 'deposit', 'withdrawal', 'transfer', 'payment',
            'finance', 'financial', 'money', 'card', 'debit', 'interest',
            'rate', 'branch', 'atm', 'online banking', 'mobile banking', 'compte',
            'banque', 'crédit', 'prêt', 'épargne', 'chèque', 'dépôt', 'retrait',
            'balance', 'solde', 'transaction', 'virement'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in banking_keywords)
    
    async def initialize_session(self):
        """Initialize the MCP session."""
        from chatbot.config import MCP_HOST, MCP_PORT
        
        mcp_url = f"http://{MCP_HOST}:{MCP_PORT}/sse"
        self.sse_client = sse_client(mcp_url)
        self.read_stream, self.write_stream = await self.sse_client.__aenter__()
        self.session = ClientSession(self.read_stream, self.write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        print("\n🔄 Connected to S2M Banking")
    
    async def close_session(self):
        """Close the MCP session."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if hasattr(self, 'sse_client'):
            await self.sse_client.__aexit__(None, None, None)
    
    def _convert_tools_to_openai_format(self):
        """Convert Gemini tool definitions to OpenAI function format."""
        openai_tools = []
        
        for tool in TOOL_DEFINITIONS:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": tool["parameters"]["properties"],
                        "required": tool["parameters"].get("required", [])
                    }
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    async def _handle_general_question(self, user_input):
        """Handle general questions without using MCP tools"""
        try:
            general_prompt = f"""
            Tu es un assistant IA utile et compétent. Réponds à cette question 
            de manière informative et précise en utilisant tes connaissances générales.
            
            Question: {user_input}
            """
            
            response = await self.general_openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": general_prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Je peux répondre à votre question sur '{user_input}', mais j'ai rencontré une erreur technique: {str(e)}"
    
    async def _process_response(self, response):
        """Process the response from OpenAI, handling function calls."""
        try:
            message = response.choices[0].message
            result = []
            
            # Handle text content
            if message.content:
                result.append(message.content)
            
            # Handle function calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    
                    # Skip empty function calls silently
                    if not function_name or function_name.strip() == "":
                        continue
                    
                    try:
                        # Parse function arguments
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Execute the function call through MCP
                        function_result = await self._execute_function_call(function_name, function_args)
                        
                        # Parse the function result to extract actual data
                        parsed_result = self._parse_function_result(function_result)
                        
                        # Format the result using the ResponseFormatter
                        formatted_result = ResponseFormatter.format_response(function_name, parsed_result)
                        if formatted_result:
                            result.append(formatted_result)
                            
                    except Exception as e:
                        error_msg = f"I'm sorry, I couldn't complete that action: {str(e)}"
                        result.append(error_msg)
            
            # Return appropriate response
            if result:
                return "\n".join(result)
            else:
                return "Hello! How can I help with your banking needs today?"
                
        except Exception as e:
            return f"Error processing response: {str(e)}"
    
    def _parse_function_result(self, result):
        """Parse the function result to extract the actual data."""
        try:
            # Check if result has content attribute (MCP response format)
            if hasattr(result, 'content') and result.content:
                # Extract text content
                text_contents = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        text_contents.append(content.text)
                
                # Try to parse each text content as JSON
                parsed_contents = []
                for text in text_contents:
                    try:
                        parsed_contents.append(json.loads(text))
                    except:
                        parsed_contents.append(text)
                
                # Special handling for get_transaction_history
                if len(parsed_contents) == 1:
                    content = parsed_contents[0]
                    # Check if this looks like a transaction object
                    if isinstance(content, dict) and all(key in content for key in ['transaction_id', 'date', 'description']):
                        return [content]
                    return content
                
                return parsed_contents
            
            # If it's a dictionary or list, return as is
            if isinstance(result, (dict, list)):
                return result
            
            # If it's a string that looks like JSON, parse it
            if isinstance(result, str):
                try:
                    if result.strip().startswith('{') or result.strip().startswith('['):
                        parsed = json.loads(result)
                        # Special handling for transaction objects
                        if isinstance(parsed, dict) and all(key in parsed for key in ['transaction_id', 'date', 'description']):
                            return [parsed]
                        return parsed
                except:
                    pass
            
            # Return as is if we couldn't parse it
            return result
        except Exception as e:
            print(f"Error parsing function result: {e}")
            return result
    
    async def _execute_function_call(self, function_name, args):
        """Execute a function call through the MCP session."""
        try:
            # Check if function name is empty or invalid
            if not function_name or function_name.strip() == "":
                return {
                    "content": "No valid function specified",
                    "skip_response": True,
                    "error": True
                }
                
            # Create a new dict from args to avoid modifying the original
            mcp_args = dict(args) if args else {}
            
            # Add user_id automatically if not provided and needed
            if function_name != "answer_banking_question" and "user_id" not in mcp_args:
                mcp_args["user_id"] = self.user_id
            
            print(f"\n🔧 Executing function: {function_name} with args: {mcp_args}")
                
            # Call the function through MCP
            result = await self.session.call_tool(function_name, mcp_args)
            
            # Format the result for logging
            result_str = self._format_result_for_logging(result)
            
            # Print the result for debugging
            print(f"\n🔧 Function Result ({function_name}):")
            print(result_str)
            
            return result
        except Exception as e:
            error_msg = f"Error executing function {function_name}: {str(e)}"
            print(f"\n❌ {error_msg}")
            return {"error": error_msg}
    
    def _format_result_for_logging(self, result):
        """Format a result object for logging."""
        try:
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2, default=str)
            return str(result)
        except Exception as e:
            print(f"Error formatting result for logging: {e}")
            return str(result)
    
    def build_conversation_history(self):
        """Build conversation history in OpenAI format."""
        messages = []
        
        # MODIFIED: System prompt more permissive
        system_prompt = f"""
        You are a helpful AI assistant specializing in S2M banking services for user {self.user_id}. 
        
        For banking-related questions, use the available tools to help customers with:
        - Account information and balances
        - Transaction history
        - Fund transfers
        - General banking questions
        
        For non-banking questions, you can provide helpful information using your general knowledge.
        
        Always be professional, helpful, and accurate in your responses.
        """
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in self.conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    async def send_message(self, user_input):
        """Send a message to the assistant and get a response."""
        # Print user input for debugging
        print(f"\n💬 User: {user_input}")
        
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Check for commands first
        command, arg = IntentDetector.detect_command(user_input)
        if command:
            if command == "exit":
                return "Goodbye! Thank you for using S2M Banking Agent."
            elif command == "clear":
                self.conversation_history = []
                return "Conversation history cleared."
            elif command == "user" and arg:
                self.user_id = arg
                return f"User ID changed to: {self.user_id}"
        
        try:
            # NOUVELLE LOGIQUE: Vérifier si c'est une question bancaire
            if not self._is_banking_related(user_input):
                # Question générale - utiliser directement OpenAI
                assistant_response = await self._handle_general_question(user_input)
                print(f"\n🔁 Assistant (General): {assistant_response}")
                self.conversation_history.append({"role": "assistant", "content": assistant_response})
                return assistant_response
            
            # Question bancaire - utiliser le système MCP
            messages = self.build_conversation_history()
            openai_tools = self._convert_tools_to_openai_format()
            
            response = await self.openai_client.chat.completions.create(
                model=MODEL_CONFIG.get("model_name", "gpt-4o-mini"),
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                temperature=MODEL_CONFIG.get("temperature", 0.7),
                max_tokens=MODEL_CONFIG.get("max_tokens", 1000)
            )
            
            # Process and print response
            assistant_response = await self._process_response(response)
            
            print(f"\n🔁 Assistant (Banking): {assistant_response}")
            
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"I'm sorry, I couldn't complete that action: {str(e)}"
            print(f"\n❌ {error_msg}")
            return error_msg
    
    async def run_interactive(self):
        """Run the assistant in interactive mode."""
        try:
            await self.initialize_session()
            
            print("\n🏦 S2M Banking Agent (Version Modifiée)")
            print("Je peux maintenant répondre à TOUTES vos questions !")
            print("Type 'exit' to quit, 'clear' to clear conversation history")
            print("Type 'user <id>' to change user ID (current: " + self.user_id + ")")
            
            while True:
                try:
                    user_input = input("\n💬 You: ")
                    
                    # Check for exit command
                    command, _ = IntentDetector.detect_command(user_input)
                    if command == "exit":
                        print("Goodbye! Thank you for using S2M Banking Agent.")
                        break
                    
                    # Process the message
                    response = await self.send_message(user_input)
                    
                    # If the response indicates exit, break the loop
                    if command == "exit":
                        break
                        
                except KeyboardInterrupt:
                    print("\nInterrupted. Exiting...")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")
                    print("Continuing...")
        finally:
            print("\nClosing connection...")
            await self.close_session()

async def main():
    """Main entry point for the interactive banking agent."""
    try:
        assistant = InteractiveBankingAssistant()
        await assistant.run_interactive()
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        print("The assistant has encountered an unrecoverable error and must exit.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")