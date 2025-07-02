import os
import re
import json
import time
import requests
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("recall_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RecallChatBot")

class RecallChatBot:
    def __init__(self, sandbox: bool = True):
        self.API_KEY = os.getenv("RECALL_API_KEY")
        if not self.API_KEY:
            logger.error("RECALL_API_KEY environment variable not found!")
            raise ValueError("API key not configured")
        
        # Set environment
        self.sandbox = sandbox
        self.BASE_URL = "https://api.sandbox.competitions.recall.network" if sandbox \
                        else "https://api.competitions.recall.network"
        
        # Token address mapping
        self.TOKENS = {
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
            "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
            "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
            "MATIC": "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0"
        }
        
        # Reverse token mapping (address to symbol)
        self.ADDRESS_TO_TOKEN = {v: k for k, v in self.TOKENS.items()}
        
        # User state tracking
        self.user_state = {}
        self.alerts = []  # Price alerts
        self.strategies = {
            "trend": "Trend following strategy",
            "meanreversion": "Mean reversion strategy",
            "arbitrage": "Arbitrage strategy",
            "random": "Random entry strategy"
        }
        
        # Commands dictionary
        self.commands = {
            "help": self.show_help,
            "trade": self.handle_trade,
            "balance": self.get_balance,
            "market": self.get_market_data,
            "history": self.get_trade_history,
            "strategy": self.set_strategy,
            "price": self.get_price,
            "alerts": self.manage_alerts,
            "portfolio": self.get_portfolio,
            "tokens": self.list_tokens,
            "exit": self.exit_bot,
            "settings": self.manage_settings
        }
        
        # Configuration
        self.config = {
            "default_trade_amount": 100,
            "max_trade_amount": 10000,
            "min_trade_amount": 10,
            "alert_check_interval": 60  # seconds
        }
        
        # Simulated data
        self.simulated_balance = {
            "USDC": 12450.75,
            "WETH": 5.32,
            "DAI": 8200.50,
            "WBTC": 0.25
        }
        
        self.simulated_prices = {
            "USDC_WETH": 0.00048,
            "WETH_BTC": 0.053,
            "USDC_DAI": 0.999,
            "WETH_UNI": 15.2,
            "USDC_WBTC": 0.000032
        }
        
        logger.info("Recall Trading Bot initialized")
        print("""
        🤖 Welcome to Recall Trading Bot!
        ---------------------------------
        Type 'help' to see available commands
        Type 'exit' to end the session
        """)
    
    def show_help(self, user_id: str, params: Optional[str] = None) -> str:
        """Display help information"""
        return """
        📚 Available Commands:
        ------------------------------
        • help - Show this help message
        • trade <from> to <to> <amount> - Execute a trade (e.g.: trade USDC to WETH 100)
        • balance - Show account balance
        • market [pair] - Show market data (e.g.: market USDC_WETH)
        • history - Show recent trade history
        • strategy <name> - Set trading strategy (options: trend, meanreversion, arbitrage, random)
        • price <pair> - Get current price for a token pair
        • alerts [add|remove|list] - Manage price alerts
        • portfolio - Show portfolio summary
        • tokens - List supported tokens
        • settings - Configure bot settings
        • exit - End the session
        """
    
    def parse_command(self, text: str) -> Tuple[str, Optional[str]]:
        """Parse natural language commands"""
        text = text.strip().lower()
        
        # Match trade command
        trade_match = re.match(r'trade\s+(\w+)\s+to\s+(\w+)\s+([\d\.]+)', text)
        if trade_match:
            return ("trade", trade_match.groups())
        
        # Match market command
        market_match = re.match(r'market\s+(\w+_\w+)', text)
        if market_match:
            return ("market", market_match.group(1))
        
        # Match strategy command
        strategy_match = re.match(r'strategy\s+(\w+)', text)
        if strategy_match:
            return ("strategy", strategy_match.group(1))
        
        # Match price command
        price_match = re.match(r'price\s+(\w+_\w+)', text)
        if price_match:
            return ("price", price_match.group(1))
        
        # Match alerts command
        alerts_match = re.match(r'alerts\s+(add|remove|list)\s*(.*)', text)
        if alerts_match:
            action = alerts_match.group(1)
            param = alerts_match.group(2).strip()
            return ("alerts", f"{action} {param}")
        
        # Match simple commands
        for cmd in self.commands:
            if text.startswith(cmd):
                return (cmd, None)
        
        return ("unknown", text)
    
    def handle_trade(self, user_id: str, params) -> str:
        """Handle trade requests"""
        if not params or len(params) != 3:
            return "❌ Format error! Correct format: trade <from_token> to <to_token> <amount>"
        
        from_token, to_token, amount = params
        from_token = from_token.upper()
        to_token = to_token.upper()
        
        # Validate tokens
        if from_token not in self.TOKENS:
            return f"❌ Invalid source token: {from_token}. Supported tokens: {', '.join(self.TOKENS.keys())}"
        
        if to_token not in self.TOKENS:
            return f"❌ Invalid target token: {to_token}. Supported tokens: {', '.join(self.TOKENS.keys())}"
        
        # Validate amount
        try:
            amount = float(amount)
            if amount < self.config["min_trade_amount"]:
                return f"❌ Amount too small. Minimum: {self.config['min_trade_amount']}"
            if amount > self.config["max_trade_amount"]:
                return f"❌ Amount too large. Maximum: {self.config['max_trade_amount']}"
        except ValueError:
            return "❌ Invalid amount. Must be a number."
        
        # Execute trade
        response = self.execute_trade(
            from_token,
            to_token,
            amount,
            f"User {user_id} initiated trade"
        )
        
        if response and response.status_code == 200:
            trade_data = response.json()
            # Update simulated balance
            self.update_simulated_balance(from_token, to_token, amount)
            return f"✅ Trade successful!\n" \
                   f"ID: {trade_data.get('id', 'N/A')}\n" \
                   f"Details: {from_token} → {to_token} {amount}\n" \
                   f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            error_msg = response.text if response else "API did not respond"
            return f"❌ Trade failed: {error_msg}"
    
    def execute_trade(self, from_token: str, to_token: str, amount: float, reason: str = "") -> Optional[requests.Response]:
        """Execute a trade"""
        payload = {
            "fromToken": self.TOKENS[from_token],
            "toToken": self.TOKENS[to_token],
            "amount": str(amount),
            "reason": reason
        }
        
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        endpoint = f"{self.BASE_URL}/api/trade/execute"
        
        try:
            logger.info(f"Executing trade: {amount} {from_token} -> {to_token}")
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            return response
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return None
    
    def update_simulated_balance(self, from_token: str, to_token: str, amount: float):
        """Update simulated balance after trade"""
        if from_token in self.simulated_balance:
            self.simulated_balance[from_token] -= amount
            if self.simulated_balance[from_token] < 0:
                self.simulated_balance[from_token] = 0
        
        # Calculate received amount using simulated price
        pair = f"{from_token}_{to_token}"
        price = self.simulated_prices.get(pair, 1.0)
        received_amount = amount * price
        
        if to_token in self.simulated_balance:
            self.simulated_balance[to_token] += received_amount
        else:
            self.simulated_balance[to_token] = received_amount
    
    def get_balance(self, user_id: str, params: Optional[str] = None) -> str:
        """Get account balance"""
        # Format balance information
        balance_info = "💰 Account Balance:\n"
        for token, amount in self.simulated_balance.items():
            balance_info += f"{token}: {amount:,.2f}\n"
        
        balance_info += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return balance_info
    
    def get_market_data(self, user_id: str, token_pair: Optional[str] = None) -> str:
        """Get market data"""
        if token_pair:
            token_pair = token_pair.upper()
            if token_pair in self.simulated_prices:
                price = self.simulated_prices[token_pair]
                change = "+2.3%" if "USDC" in token_pair else "-1.2%"
                volume = "42.5M" if "USDC" in token_pair else "18.2M"
                
                return f"📊 {token_pair} Market Data:\n" \
                       f"Price: {price}\n" \
                       f"24h Change: {change}\n" \
                       f"Volume: {volume}"
            else:
                return f"❌ No data for {token_pair}. Available pairs: {', '.join(self.simulated_prices.keys())}"
        else:
            market_info = "📊 Market Overview:\n"
            for pair, price in self.simulated_prices.items():
                change = "+2.3%" if "USDC" in pair else "-1.2%"
                market_info += f"• {pair}: {price} ({change})\n"
            return market_info
    
    def get_trade_history(self, user_id: str, params: Optional[str] = None) -> str:
        """Get trade history"""
        history = [
            {"id": "TX001", "pair": "USDC→WETH", "amount": 100, "time": "2023-08-10 14:30", "status": "completed"},
            {"id": "TX002", "pair": "WETH→DAI", "amount": 0.5, "time": "2023-08-10 09:15", "status": "completed"},
            {"id": "TX003", "pair": "DAI→USDC", "amount": 500, "time": "2023-08-09 16:45", "status": "completed"},
            {"id": "TX004", "pair": "USDC→UNI", "amount": 200, "time": "2023-08-09 10:20", "status": "pending"}
        ]
        
        history_info = "📜 Recent Trade History:\n"
        for trade in history:
            history_info += f"{trade['time']} - {trade['pair']} {trade['amount']} ({trade['status']})\n"
        
        return history_info
    
    def set_strategy(self, user_id: str, strategy_name: Optional[str] = None) -> str:
        """Set trading strategy"""
        if not strategy_name:
            current = self.user_state.get(user_id, {}).get("strategy", "none")
            return f"Current strategy: {current}\nAvailable strategies: {', '.join(self.strategies.keys())}"
        
        strategy_name = strategy_name.lower()
        if strategy_name in self.strategies:
            # Initialize user state if not exists
            if user_id not in self.user_state:
                self.user_state[user_id] = {}
                
            self.user_state[user_id]["strategy"] = strategy_name
            return f"✅ Strategy set: {self.strategies[strategy_name]}"
        else:
            return f"❌ Invalid strategy! Available: {', '.join(self.strategies.keys())}"
    
    def get_price(self, user_id: str, token_pair: Optional[str] = None) -> str:
        """Get current price for a token pair"""
        if not token_pair:
            return "❌ Please specify a token pair (e.g.: price USDC_WETH)"
        
        token_pair = token_pair.upper()
        if token_pair in self.simulated_prices:
            price = self.simulated_prices[token_pair]
            return f"💵 Current price for {token_pair}: {price}"
        else:
            return f"❌ No price data for {token_pair}. Available pairs: {', '.join(self.simulated_prices.keys())}"
    
    def manage_alerts(self, user_id: str, action_params: Optional[str] = None) -> str:
        """Manage price alerts"""
        if not action_params:
            return "❌ Specify an action: alerts add <pair> <price>, alerts remove <id>, alerts list"
        
        parts = action_params.split()
        action = parts[0] if parts else None
        
        # Initialize alerts for user
        if user_id not in self.user_state:
            self.user_state[user_id] = {"alerts": []}
        elif "alerts" not in self.user_state[user_id]:
            self.user_state[user_id]["alerts"] = []
        
        alerts = self.user_state[user_id]["alerts"]
        
        if action == "add" and len(parts) >= 3:
            try:
                pair = parts[1].upper()
                target_price = float(parts[2])
                alert_id = f"ALERT-{len(alerts)+1}"
                
                alert = {
                    "id": alert_id,
                    "pair": pair,
                    "target_price": target_price,
                    "created": datetime.now().isoformat(),
                    "triggered": False
                }
                
                alerts.append(alert)
                return f"✅ Alert added: {pair} @ {target_price} (ID: {alert_id})"
            except ValueError:
                return "❌ Invalid price. Must be a number."
        
        elif action == "remove" and len(parts) >= 2:
            alert_id = parts[1]
            for i, alert in enumerate(alerts):
                if alert["id"] == alert_id:
                    del alerts[i]
                    return f"✅ Alert removed: {alert_id}"
            return f"❌ Alert not found: {alert_id}"
        
        elif action == "list":
            if not alerts:
                return "🔔 No active alerts"
            
            alert_list = "🔔 Your Price Alerts:\n"
            for alert in alerts:
                status = "ACTIVE" if not alert["triggered"] else "TRIGGERED"
                alert_list += f"• {alert['id']}: {alert['pair']} @ {alert['target_price']} ({status})\n"
            return alert_list
        
        else:
            return "❌ Invalid alert command. Use: alerts add <pair> <price>, alerts remove <id>, alerts list"
    
    def check_alerts(self):
        """Check if any price alerts have been triggered"""
        for user_id, state in self.user_state.items():
            if "alerts" in state:
                for alert in state["alerts"]:
                    if not alert["triggered"]:
                        current_price = self.simulated_prices.get(alert["pair"], None)
                        if current_price is not None:
                            # Simple trigger check (current price crosses target price)
                            if current_price >= alert["target_price"]:
                                alert["triggered"] = True
                                return f"🚨 Price alert triggered for {user_id}: {alert['pair']} reached {current_price} (target: {alert['target_price']})"
        return None
    
    def get_portfolio(self, user_id: str, params: Optional[str] = None) -> str:
        """Get portfolio summary"""
        # Calculate total value in USDC
        total_value = 0
        portfolio_info = "📊 Portfolio Summary:\n"
        
        for token, amount in self.simulated_balance.items():
            if token == "USDC":
                value = amount
            else:
                pair = f"{token}_USDC"
                price = self.simulated_prices.get(pair, 1.0)  # Default to 1 if no price
                value = amount * price
            
            total_value += value
            portfolio_info += f"• {token}: {amount:,.4f} (≈ ${value:,.2f})\n"
        
        portfolio_info += f"\n💵 Total Value: ${total_value:,.2f}"
        portfolio_info += f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return portfolio_info
    
    def list_tokens(self, user_id: str, params: Optional[str] = None) -> str:
        """List supported tokens"""
        token_list = "🪙 Supported Tokens:\n"
        for token, address in self.TOKENS.items():
            token_list += f"• {token} ({address[:6]}...{address[-4:]})\n"
        return token_list
    
    def manage_settings(self, user_id: str, params: Optional[str] = None) -> str:
        """Manage bot settings"""
        if not params:
            settings_info = "⚙️ Current Settings:\n"
            for key, value in self.config.items():
                settings_info += f"• {key}: {value}\n"
            return settings_info
        
        parts = params.split()
        if len(parts) == 2:
            setting, value = parts
            if setting in self.config:
                try:
                    # Convert to appropriate type
                    if isinstance(self.config[setting], float):
                        new_value = float(value)
                    elif isinstance(self.config[setting], int):
                        new_value = int(value)
                    else:
                        new_value = value
                    
                    self.config[setting] = new_value
                    return f"✅ Setting updated: {setting} = {new_value}"
                except ValueError:
                    return f"❌ Invalid value for {setting}. Must be {type(self.config[setting]).__name__}"
            else:
                return f"❌ Unknown setting: {setting}"
        else:
            return "❌ Invalid format. Use: settings <name> <value>"
    
    def exit_bot(self, user_id: str, params: Optional[str] = None) -> str:
        """End the session"""
        return "👋 Thank you for using Recall Trading Bot! Goodbye!"
    
    def start_chat(self):
        """Start the chat session"""
        print("💬 Chat mode activated (type 'exit' to end)")
        last_alert_check = time.time()
        
        try:
            while True:
                # Check for price alerts periodically
                current_time = time.time()
                if current_time - last_alert_check > self.config["alert_check_interval"]:
                    alert_message = self.check_alerts()
                    if alert_message:
                        print(f"\n🤖 Recall: {alert_message}")
                    last_alert_check = current_time
                
                try:
                    user_input = input("\n👤 You: ").strip()
                    if not user_input:
                        continue
                    
                    # User ID (in a real system, this would come from authentication)
                    user_id = "user_001"
                    
                    # Parse command
                    command, params = self.parse_command(user_input)
                    
                    # Execute command
                    if command in self.commands:
                        response = self.commands[command](user_id, params)
                        print(f"\n🤖 Recall: {response}")
                        
                        # Check for exit command
                        if command == "exit":
                            break
                    else:
                        print(f"\n🤖 Recall: I didn't understand '{user_input}'. Type 'help' for available commands")
                
                except KeyboardInterrupt:
                    print("\n🛑 Session interrupted")
                    break
                except Exception as e:
                    print(f"\n🤖 Recall: Processing error - {str(e)}")
                    logger.error(f"Command processing error: {str(e)}")
        
        finally:
            logger.info("Chat session ended")
            print("Session ended. Logs saved to recall_bot.log")

if __name__ == "__main__":
    try:
        bot = RecallChatBot(sandbox=True)
        bot.start_chat()
    except Exception as e:
        print(f"Failed to start bot: {str(e)}")
        logger.exception("Bot startup failed")