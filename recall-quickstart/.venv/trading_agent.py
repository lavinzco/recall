import os
import time
import json
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# 加载环境变量
load_dotenv()

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("trading_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RecallTradingAgent")

class RecallTradingAgent:
    def __init__(self, sandbox: bool = True):
        """
        初始化交易代理
        
        :param sandbox: 是否使用沙盒环境
        """
        self.API_KEY = os.getenv("RECALL_API_KEY")
        if not self.API_KEY:
            logger.error("未找到RECALL_API_KEY环境变量！")
            raise ValueError("API密钥未配置")
        
        # 设置环境
        self.sandbox = sandbox
        self.BASE_URL = "https://api.sandbox.competitions.recall.network" if sandbox \
                        else "https://api.competitions.recall.network"
        
        # 常用代币地址映射
        self.TOKENS = {
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
            "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA"
        }
        
        # 配置参数
        self.config = {
            "trade_interval": 300,  # 交易检查间隔（秒）
            "max_trade_amount": 1000,  # 单次最大交易金额
            "min_trade_amount": 10,   # 单次最小交易金额
            "trade_pairs": [("USDC", "WETH"), ("DAI", "USDC")],  # 常用交易对
            "risk_factor": 0.02,  # 每次交易最大风险比例（占总投资额）
            "stop_loss": 0.05,    # 止损比例
            "take_profit": 0.10   # 止盈比例
        }
        
        # 状态跟踪
        self.last_trade_time = None
        self.trade_history = []
        self.balance = self.get_initial_balance()
        self.strategy = "trend_following"  # 默认策略
        
        logger.info("Recall交易代理初始化完成")
        logger.info(f"运行环境: {'沙盒' if sandbox else '生产'}")
    
    def get_initial_balance(self) -> Dict[str, float]:
        """获取初始模拟余额"""
        return {
            "USDC": 10000.0,
            "WETH": 5.0,
            "DAI": 5000.0
        }
    
    def get_market_data(self, token_pair: str) -> Optional[dict]:
        """
        获取市场数据（模拟实现）
        
        :param token_pair: 交易对，如 "USDC_WETH"
        :return: 市场数据字典
        """
        # 在实际应用中应替换为真实API调用
        # 示例: response = requests.get(f"{self.BASE_URL}/market/{token_pair}")
        base_token, quote_token = token_pair.split("_")
        
        # 模拟市场数据
        return {
            "pair": token_pair,
            "price": 0.00048 if token_pair == "USDC_WETH" else 1.001,
            "24h_change": 0.023,  # 2.3%
            "24h_high": 0.00050,
            "24h_low": 0.00046,
            "volume": 42000000,  # 42M
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_portfolio(self) -> Dict[str, float]:
        """
        获取当前投资组合（模拟实现）
        
        :return: 代币余额字典
        """
        # 在实际应用中应替换为真实API调用
        # 示例: response = requests.get(f"{self.BASE_URL}/portfolio", headers={"Authorization": f"Bearer {self.API_KEY}"})
        return self.balance
    
    def execute_trade(self, from_token: str, to_token: str, amount: float, reason: str = "") -> Optional[dict]:
        """
        执行交易操作
        
        :param from_token: 来源代币符号
        :param to_token: 目标代币符号
        :param amount: 交易数量
        :param reason: 交易原因
        :return: 交易响应数据
        """
        # 验证代币
        if from_token not in self.TOKENS:
            logger.error(f"无效来源代币: {from_token}")
            return None
            
        if to_token not in self.TOKENS:
            logger.error(f"无效目标代币: {to_token}")
            return None
        
        # 验证金额
        if amount < self.config["min_trade_amount"]:
            logger.warning(f"交易金额过小: {amount} {from_token} < {self.config['min_trade_amount']}")
            return None
            
        if amount > self.config["max_trade_amount"]:
            logger.warning(f"交易金额过大: {amount} {from_token} > {self.config['max_trade_amount']}")
            return None
        
        # 检查余额
        if self.balance.get(from_token, 0) < amount:
            logger.error(f"余额不足: 需要 {amount} {from_token}, 实际 {self.balance.get(from_token, 0)}")
            return None
        
        # 准备请求
        endpoint = f"{self.BASE_URL}/api/trade/execute"
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
        
        logger.info(f"执行交易: {amount} {from_token} -> {to_token}")
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                trade_data = response.json()
                logger.info(f"交易成功! ID: {trade_data.get('id', 'N/A')}")
                
                # 更新本地状态（模拟）
                self.update_balance_after_trade(from_token, to_token, amount, trade_data)
                self.record_trade(from_token, to_token, amount, trade_data)
                
                return trade_data
            else:
                logger.error(f"交易失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.exception(f"交易请求异常: {str(e)}")
            return None
    
    def update_balance_after_trade(self, from_token: str, to_token: str, amount: float, trade_data: dict):
        """
        交易后更新本地余额（模拟）
        
        :param from_token: 来源代币
        :param to_token: 目标代币
        :param amount: 交易数量
        :param trade_data: 交易响应数据
        """
        # 在实际应用中应从API获取最新余额
        # 这里简单模拟：减少来源代币，增加目标代币
        
        # 模拟价格（实际应从trade_data获取）
        price = 0.0005 if from_token == "USDC" and to_token == "WETH" else 1.0
        
        # 更新余额
        self.balance[from_token] = max(0, self.balance.get(from_token, 0) - amount)
        
        received_amount = amount * price
        self.balance[to_token] = self.balance.get(to_token, 0) + received_amount
        
        logger.info(f"余额更新: -{amount} {from_token}, +{received_amount:.6f} {to_token}")
    
    def record_trade(self, from_token: str, to_token: str, amount: float, trade_data: dict):
        """
        记录交易历史
        
        :param from_token: 来源代币
        :param to_token: 目标代币
        :param amount: 交易数量
        :param trade_data: 交易响应数据
        """
        trade_record = {
            "id": trade_data.get("id", f"local-{int(time.time())}"),
            "from_token": from_token,
            "to_token": to_token,
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": trade_data.get("reason", ""),
            "status": "executed"
        }
        
        self.trade_history.append(trade_record)
        logger.info(f"交易记录: {trade_record}")
    
    def trend_following_strategy(self) -> Optional[Tuple[str, str, float]]:
        """
        趋势跟踪策略
        
        :return: (from_token, to_token, amount) 或 None
        """
        # 获取市场数据
        market_data = self.get_market_data("USDC_WETH")
        
        if not market_data:
            return None
        
        # 简单趋势策略：如果24小时涨幅超过2%，则买入
        price_change = market_data["24h_change"]
        
        if price_change > 0.02:  # 2% 上涨
            amount = min(100, self.balance.get("USDC", 0) * self.config["risk_factor"])
            return ("USDC", "WETH", amount)
        
        # 如果下跌超过1%，则卖出
        elif price_change < -0.01:
            amount = min(0.1, self.balance.get("WETH", 0) * self.config["risk_factor"])
            return ("WETH", "USDC", amount)
        
        return None
    
    def mean_reversion_strategy(self) -> Optional[Tuple[str, str, float]]:
        """
        均值回归策略
        
        :return: (from_token, to_token, amount) 或 None
        """
        # 获取市场数据
        market_data = self.get_market_data("USDC_WETH")
        
        if not market_data:
            return None
        
        current_price = market_data["price"]
        mean_price = (market_data["24h_high"] + market_data["24h_low"]) / 2
        
        # 如果当前价格低于均值一定比例，买入
        if current_price < mean_price * 0.98:  # 低于均值2%
            amount = min(100, self.balance.get("USDC", 0) * self.config["risk_factor"])
            return ("USDC", "WETH", amount)
        
        # 如果当前价格高于均值一定比例，卖出
        elif current_price > mean_price * 1.02:  # 高于均值2%
            amount = min(0.1, self.balance.get("WETH", 0) * self.config["risk_factor"])
            return ("WETH", "USDC", amount)
        
        return None
    
    def execute_strategy(self):
        """执行当前策略"""
        if self.strategy == "trend_following":
            return self.trend_following_strategy()
        elif self.strategy == "mean_reversion":
            return self.mean_reversion_strategy()
        else:
            logger.warning(f"未知策略: {self.strategy}")
            return None
    
    def check_stop_conditions(self):
        """检查止损止盈条件"""
        # 这里简化实现，实际中应根据持仓和当前价格计算
        # 获取当前持仓的市值
        portfolio_value = sum(
            self.balance[token] * (1 / 0.0005 if token == "WETH" else 1)  # 简化估值
            for token in self.balance
        )
        
        # 计算初始投资（简化）
        initial_investment = 15000  # 初始投资额
        
        # 检查止损
        if portfolio_value < initial_investment * (1 - self.config["stop_loss"]):
            logger.warning(f"触发止损! 当前价值: {portfolio_value:.2f}, 初始投资: {initial_investment}")
            # 实际中应执行止损操作
            return True
        
        # 检查止盈
        if portfolio_value > initial_investment * (1 + self.config["take_profit"]):
            logger.info(f"达到止盈点! 当前价值: {portfolio_value:.2f}, 初始投资: {initial_investment}")
            # 实际中可执行部分止盈
            return True
        
        return False
    
    def health_check(self):
        """执行健康检查"""
        logger.info("执行健康检查...")
        
        # 检查API连接
        try:
            response = requests.get(
                f"{self.BASE_URL}/health",
                headers={"Authorization": f"Bearer {self.API_KEY}"},
                timeout=10
            )
            if response.status_code == 200:
                logger.info("API健康状态: 正常")
            else:
                logger.warning(f"API健康状态异常: {response.status_code}")
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
        
        # 检查余额
        portfolio = self.get_portfolio()
        logger.info(f"当前余额: {json.dumps(portfolio, indent=2)}")
        
        # 检查最近交易
        if self.trade_history:
            last_trade = self.trade_history[-1]
            logger.info(f"最近交易: {last_trade['from_token']} -> {last_trade['to_token']} {last_trade['amount']}")
        else:
            logger.info("无交易历史")
    
    def run(self):
        """主运行循环"""
        logger.info("🚀 启动Recall交易代理")
        
        # 初始健康检查
        self.health_check()
        
        try:
            while True:
                start_time = time.time()
                
                try:
                    # 检查止损止盈条件
                    if self.check_stop_conditions():
                        logger.warning("满足停止条件，考虑调整策略或停止交易")
                        # 在实际应用中，可能需要暂停交易或通知用户
                    
                    # 执行交易策略
                    trade_decision = self.execute_strategy()
                    
                    if trade_decision:
                        from_token, to_token, amount = trade_decision
                        reason = f"{self.strategy}策略交易"
                        self.execute_trade(from_token, to_token, amount, reason)
                    
                    # 定期健康检查（每小时一次）
                    if not self.last_trade_time or (datetime.utcnow() - self.last_trade_time) > timedelta(hours=1):
                        self.health_check()
                    
                except Exception as e:
                    logger.exception(f"主循环异常: {str(e)}")
                
                # 计算剩余等待时间
                elapsed = time.time() - start_time
                sleep_time = max(1, self.config["trade_interval"] - elapsed)
                
                logger.info(f"下次检查在 {sleep_time:.1f} 秒后...")
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 代理停止")
        finally:
            # 保存最终状态
            self.save_state()
            logger.info("代理已安全停止")
    
    def save_state(self):
        """保存代理状态到文件"""
        state = {
            "balance": self.balance,
            "trade_history": self.trade_history,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        try:
            with open("agent_state.json", "w") as f:
                json.dump(state, f, indent=2)
            logger.info("状态已保存到 agent_state.json")
        except Exception as e:
            logger.error(f"保存状态失败: {str(e)}")

if __name__ == "__main__":
    # 创建并运行代理
    try:
        agent = RecallTradingAgent(sandbox=True)
        agent.run()
    except Exception as e:
        logger.exception("代理启动失败")
        print(f"严重错误: {str(e)}")
        print("请检查日志文件 trading_agent.log 获取详细信息")