import os
import re
import json
import time
import requests
import logging
import threading
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("trading_chatbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradingChatSystem")

class TradingChatSystem:
    def __init__(self, sandbox: bool = True):
        self.API_KEY = os.getenv("RECALL_API_KEY")
        if not self.API_KEY:
            logger.error("RECALL_API_KEY environment variable not found!")
            raise ValueError("API key not configured")
        
        # Set environment
        self.sandbox = sandbox
        self.BASE_URL = "https://api.sandbox.competitions.recall.network" if sandbox \
                        else "https://api.competitions.recall.network"
        self.TRADE_ENDPOINT = f"{self.BASE_URL}/api/trade/execute"
        
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
            "trend": "Trend following",
            "meanreversion": "Mean reversion",
            "arbitrage": "Arbitrage",
            "random": "Random entry"
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
            "settings": self.manage_settings,
            "start": self.start_auto_trading,
            "stop": self.stop_auto_trading,
            "status": self.get_system_status
        }
        
        # Trading configuration
        self.config = {
            "default_trade_amount": 100,
            "max_trade_amount": 10000,
            "min_trade_amount": 10,
            "alert_check_interval": 60,  # seconds
            "trade_interval": 300,       # seconds for auto-trading
            "risk_factor": 0.02,         # % of portfolio per trade
            "stop_loss": 0.05,           # 5% stop loss
            "take_profit": 0.10          # 10% take profit
        }
        
        # Trading state
        self.balance = self.get_initial_balance()
        self.trade_history = []
        self.active_strategy = None
        self.auto_trading_active = False
        self.auto_trading_thread = None
        self.stop_event = threading.Event()
        
        # Market data (simulated or from API)
        self.market_data = self.initialize_market_data()
        
        logger.info("Trading Chat System initialized")
        print("""
        🤖 Welcome to Recall Trading System!
        ------------------------------------
        Type 'help' to see available commands
        Type 'exit' to end the session
        
        Features:
        • Manual trading via chat commands
        • Auto-trading with configurable strategies
        • Portfolio management and alerts
        • Real-time market data
        """)
    
    def get_initial_balance(self) -> Dict[str, float]:
        """Get initial balance from API or simulation"""
        # In a real system, this would come from the API
        return {
            "USDC": 10000.0,
            "WETH": 5.0,
            "DAI": 5000.0,
            "WBTC": 0.25
        }
    
    def initialize_market_data(self) -> Dict[str, Dict[str, Any]]:
        """Initialize market data (simulated or from API)"""
        return {
            "USDC_WETH": {
                "price": 0.00048,
                "24h_change": 0.023,
                "24h_high": 0.00050,
                "24h_low": 0.00046,
                "volume": 42500000
            },
            "WETH_BTC": {
                "price": 0.053,
                "24h_change": -0.012,
                "24h_high": 0.055,
                "24h_low": 0.052,
                "volume": 18200000
            },
            "USDC_DAI": {
                "price": 0.999,
                "24h_change": 0.001,
                "24h_high": 1.001,
                "24h_low": 0.998,
                "volume": 28700000
            },
            "WETH_UNI": {
                "price": 15.2,
                "24h_change": 0.018,
                "24h_high": 15.5,
                "24h_low": 14.9,
                "volume": 5200000
            },
            "USDC_WBTC": {
                "price": 0.000032,
                "24h_change": -0.005,
                "24h_high": 0.000033,
                "24h_low": 0.000031,
                "volume": 18300000
            }
        }
    
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
        • start - Start auto-trading
        • stop - Stop auto-trading
        • status - Show system status
        • exit - End the session
        
        💡 Examples:
        • "trade USDC to WETH 200"
        • "market USDC_WETH"
        • "strategy trend"
        • "alerts add WETH_BTC 0.055"
        • "portfolio"
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
        
        # Check balance
        if from_token not in self.balance or self.balance[from_token] < amount:
            return f"❌ Insufficient balance. Available {from_token}: {self.balance.get(from_token, 0):.2f}"
        
        # Execute trade
        success, trade_data = self.execute_trade(
            from_token,
            to_token,
            amount,
            f"User {user_id} initiated trade"
        )
        
        if success:
            return f"✅ Trade successful!\n" \
                   f"ID: {trade_data.get('id', 'N/A')}\n" \
                   f"Details: {from_token} → {to_token} {amount}\n" \
                   f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            return f"❌ Trade failed: {trade_data}"
    
    def execute_trade(self, from_token: str, to_token: str, amount: float, reason: str = "") -> Tuple[bool, dict]:
        """Execute a trade and update local state"""
        # In a real system, this would call the API
        # For simulation, we'll update balances and create a trade record
        
        # Calculate price and received amount
        pair = f"{from_token}_{to_token}"
        reverse_pair = f"{to_token}_{from_token}"
        
        if pair in self.market_data:
            price = self.market_data[pair]["price"]
        elif reverse_pair in self.market_data:
            price = 1 / self.market_data[reverse_pair]["price"]
        else:
            # Default to 1:1 if no price data
            price = 1.0
        
        received_amount = amount * price
        
        # Update balances
        self.balance[from_token] -= amount
        if to_token in self.balance:
            self.balance[to_token] += received_amount
        else:
            self.balance[to_token] = received_amount
        
        # Create trade record
        trade_id = f"TRADE-{len(self.trade_history) + 1}-{int(time.time())}"
        trade_record = {
            "id": trade_id,
            "from_token": from_token,
            "to_token": to_token,
            "amount": amount,
            "received": received_amount,
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "status": "executed"
        }
        
        self.trade_history.append(trade_record)
        logger.info(f"Trade executed: {from_token} -> {to_token} {amount}")
        
        return True, trade_record
    
    def get_balance(self, user_id: str, params: Optional[str] = None) -> str:
        """Get account balance"""
        balance_info = "💰 Account Balance:\n"
        for token, amount in self.balance.items():
            balance_info += f"{token}: {amount:,.4f}\n"
        
        balance_info += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return balance_info
    
    def get_market_data(self, user_id: str, token_pair: Optional[str] = None) -> str:
        """Get market data"""
        if token_pair:
            token_pair = token_pair.upper()
            if token_pair in self.market_data:
                data = self.market_data[token_pair]
                change_percent = data["24h_change"] * 100
                change_sign = "+" if change_percent >= 0 else ""
                volume = f"{data['volume']/1000000:.1f}M"
                
                return f"📊 {token_pair} Market Data:\n" \
                       f"Price: {data['price']:.6f}\n" \
                       f"24h Change: {change_sign}{change_percent:.2f}%\n" \
                       f"24h High: {data['24h_high']:.6f}\n" \
                       f"24h Low: {data['24h_low']:.6f}\n" \
                       f"Volume: {volume}"
            else:
                return f"❌ No data for {token_pair}. Available pairs: {', '.join(self.market_data.keys())}"
        else:
            market_info = "📊 Market Overview:\n"
            for pair, data in self.market_data.items():
                change_percent = data["24h_change"] * 100
                change_sign = "+" if change_percent >= 0 else ""
                market_info += f"• {pair}: {data['price']:.6f} ({change_sign}{change_percent:.2f}%)\n"
            return market_info
    
    def get_trade_history(self, user_id: str, params: Optional[str] = None) -> str:
        """Get trade history"""
        if not self.trade_history:
            return "📜 No trade history yet"
        
        history_info = "📜 Recent Trade History:\n"
        for trade in self.trade_history[-5:][::-1]:  # Show last 5 trades, most recent first
            history_info += f"{trade['timestamp'][:19]} - " \
                            f"{trade['from_token']}→{trade['to_token']} " \
                            f"{trade['amount']:.2f} @ {trade['price']:.6f}\n"
        
        return history_info
    
    def set_strategy(self, user_id: str, strategy_name: Optional[str] = None) -> str:
        """Set trading strategy"""
        if not strategy_name:
            return f"Current strategy: {self.active_strategy or 'none'}\nAvailable strategies: {', '.join(self.strategies.keys())}"
        
        strategy_name = strategy_name.lower()
        if strategy_name in self.strategies:
            self.active_strategy = strategy_name
            return f"✅ Strategy set: {self.strategies[strategy_name]}"
        else:
            return f"❌ Invalid strategy! Available: {', '.join(self.strategies.keys())}"
    
    def get_price(self, user_id: str, token_pair: Optional[str] = None) -> str:
        """Get current price for a token pair"""
        if not token_pair:
            return "❌ Please specify a token pair (e.g.: price USDC_WETH)"
        
        token_pair = token_pair.upper()
        if token_pair in self.market_data:
            price = self.market_data[token_pair]["price"]
            return f"💵 Current price for {token_pair}: {price:.6f}"
        else:
            return f"❌ No price data for {token_pair}. Available pairs: {', '.join(self.market_data.keys())}"
    
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
    
    def check_alerts(self) -> Optional[str]:
        """Check if any price alerts have been triggered"""
        for user_id, state in self.user_state.items():
            if "alerts" in state:
                for alert in state["alerts"]:
                    if not alert["triggered"]:
                        pair = alert["pair"]
                        if pair in self.market_data:
                            current_price = self.market_data[pair]["price"]
                            # Simple trigger check
                            if current_price >= alert["target_price"]:
                                alert["triggered"] = True
                                return f"🚨 Price alert triggered: {pair} reached {current_price:.6f} (target: {alert['target_price']})"
        return None
    
    def get_portfolio(self, user_id: str, params: Optional[str] = None) -> str:
        """Get portfolio summary"""
        # Calculate total value in USDC
        total_value = 0
        portfolio_info = "📊 Portfolio Summary:\n"
        
        for token, amount in self.balance.items():
            if token == "USDC":
                value = amount
            else:
                pair = f"{token}_USDC"
                if pair in self.market_data:
                    price = self.market_data[pair]["price"]
                else:
                    # Estimate with ETH price if direct pair not available
                    eth_price = self.market_data["WETH_USDC"]["price"] if "WETH_USDC" in self.market_data else 2000
                    price = eth_price  # Simplification
                
                value = amount * price
            
            total_value += value
            portfolio_info += f"• {token}: {amount:,.4f} (≈ ${value:,.2f})\n"
        
        portfolio_info += f"\n💵 Total Value: ${total_value:,.2f}"
        portfolio_info += f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return portfolio_info
    
    def list_tokens(self, user_id: str, params: Optional[str] = None) -> str:
        """List supported tokens"""
        token_list = "🪙 Supported Tokens:\n"
        for token in self.TOKENS.keys():
            token_list += f"• {token}\n"
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
    
    def start_auto_trading(self, user_id: str, params: Optional[str] = None) -> str:
        """Start auto-trading with current strategy"""
        if not self.active_strategy:
            return "❌ No strategy set! Use 'strategy <name>' first"
        
        if self.auto_trading_active:
            return "✅ Auto-trading is already running"
        
        self.auto_trading_active = True
        self.stop_event.clear()
        
        # Start auto-trading in a separate thread
        self.auto_trading_thread = threading.Thread(
            target=self.auto_trading_loop, 
            daemon=True
        )
        self.auto_trading_thread.start()
        
        return f"✅ Auto-trading started with {self.strategies[self.active_strategy]} strategy"
    
    def stop_auto_trading(self, user_id: str, params: Optional[str] = None) -> str:
        """Stop auto-trading"""
        if not self.auto_trading_active:
            return "❌ Auto-trading is not running"
        
        self.auto_trading_active = False
        self.stop_event.set()
        return "✅ Auto-trading stopped"
    
    def get_system_status(self, user_id: str, params: Optional[str] = None) -> str:
        """Get system status"""
        status = "📡 System Status:\n"
        status += f"• Auto-trading: {'ACTIVE' if self.auto_trading_active else 'INACTIVE'}\n"
        status += f"• Strategy: {self.active_strategy or 'None'}\n"
        status += f"• Trades executed: {len(self.trade_history)}\n"
        status += f"• Last trade: {self.trade_history[-1]['timestamp'][:19] if self.trade_history else 'Never'}\n"
        status += f"• Uptime: {timedelta(seconds=int(time.time() - self.start_time))}"
        return status
    
    def auto_trading_loop(self):
        """Main loop for auto-trading"""
        logger.info("Auto-trading started")
        last_trade_time = time.time()
        
        while self.auto_trading_active and not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Check if it's time to trade
                if current_time - last_trade_time > self.config["trade_interval"]:
                    trade_decision = self.generate_trade_decision()
                    
                    if trade_decision:
                        from_token, to_token, amount = trade_decision
                        reason = f"Auto-trade: {self.strategies[self.active_strategy]} strategy"
                        success, _ = self.execute_trade(from_token, to_token, amount, reason)
                        
                        if success:
                            logger.info(f"Auto-trade executed: {from_token} -> {to_token} {amount}")
                            last_trade_time = current_time
                
                # Check alerts
                alert_msg = self.check_alerts()
                if alert_msg:
                    logger.info(f"Alert triggered: {alert_msg}")
                    # In a real system, this would notify the user
                
                # Sleep before next iteration
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in auto-trading loop: {str(e)}")
                time.sleep(10)
        
        logger.info("Auto-trading stopped")
    
    def generate_trade_decision(self) -> Optional[Tuple[str, str, float]]:
        """Generate trade decision based on active strategy"""
        if not self.active_strategy:
            return None
        
        if self.active_strategy == "trend":
            return self.trend_following_strategy()
        elif self.active_strategy == "meanreversion":
            return self.mean_reversion_strategy()
        elif self.active_strategy == "random":
            return self.random_strategy()
        else:
            return None
    
    def trend_following_strategy(self) -> Optional[Tuple[str, str, float]]:
        """Trend following strategy"""
        # For simplicity, we'll use a single pair
        pair = "USDC_WETH"
        if pair not in self.market_data:
            return None
        
        data = self.market_data[pair]
        price_change = data["24h_change"]
        
        # If price increased significantly, buy
        if price_change > 0.02:  # 2% increase
            amount = min(
                self.config["default_trade_amount"],
                self.balance.get("USDC", 0) * self.config["risk_factor"]
            )
            return ("USDC", "WETH", amount)
        
        # If price decreased significantly, sell
        elif price_change < -0.01:  # 1% decrease
            amount = min(
                0.1,  # Max 0.1 ETH
                self.balance.get("WETH", 0) * self.config["risk_factor"]
            )
            return ("WETH", "USDC", amount)
        
        return None
    
    def mean_reversion_strategy(self) -> Optional[Tuple[str, str, float]]:
        """Mean reversion strategy"""
        pair = "USDC_WETH"
        if pair not in self.market_data:
            return None
        
        data = self.market_data[pair]
        current_price = data["price"]
        mean_price = (data["24h_high"] + data["24h_low"]) / 2
        
        # If current price is below mean, buy
        if current_price < mean_price * 0.98:  # 2% below mean
            amount = min(
                self.config["default_trade_amount"],
                self.balance.get("USDC", 0) * self.config["risk_factor"]
            )
            return ("USDC", "WETH", amount)
        
        # If current price is above mean, sell
        elif current_price > mean_price * 1.02:  # 2% above mean
            amount = min(
                0.1,  # Max 0.1 ETH
                self.balance.get("WETH", 0) * self.config["risk_factor"]
            )
            return ("WETH", "USDC", amount)
        
        return None
    
    def random_strategy(self) -> Optional[Tuple[str, str, float]]:
        """Random trading strategy (for testing)"""
        import random
        
        tokens = list(self.TOKENS.keys())
        if len(tokens) < 2:
            return None
        
        from_token = random.choice(tokens)
        to_token = random.choice([t for t in tokens if t != from_token])
        
        # Get a reasonable amount
        max_amount = self.balance.get(from_token, 0)
        if max_amount > 0:
            amount = min(
                random.uniform(10, 100),
                max_amount * self.config["risk_factor"]
            )
            return (from_token, to_token, amount)
        
        return None
    
    def exit_bot(self, user_id: str, params: Optional[str] = None) -> str:
        """End the session"""
        self.stop_auto_trading(user_id, None)
        return "👋 Thank you for using Recall Trading System! Goodbye!"
    
    def start_chat(self):
        """Start the chat interface"""
        self.start_time = time.time()
        print("💬 Trading Chat activated (type 'exit' to end)")
        last_alert_check = time.time()
        
        try:
            while True:
                # Check for price alerts periodically
                current_time = time.time()
                if current_time - last_alert_check > self.config["alert_check_interval"]:
                    alert_message = self.check_alerts()
                    if alert_message:
                        print(f"\n🤖 System: {alert_message}")
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
            print("Session ended. Logs saved to trading_chatbot.log")

if __name__ == "__main__":
    try:
        system = TradingChatSystem(sandbox=True)
        system.start_chat()
    except Exception as e:
        print(f"Failed to start system: {str(e)}")
        logger.exception("System startup failed")