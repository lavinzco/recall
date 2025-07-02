import os
import requests
from dotenv import load_dotenv
import time

# 加载环境变量
load_dotenv()

class RecallTradingAgent:
    def __init__(self):
        self.API_KEY = os.getenv("RECALL_API_KEY")
        self.BASE_URL = "https://api.sandbox.competitions.recall.network"
        self.ENDPOINT = f"{self.BASE_URL}/api/trade/execute"
        
        # 常用代币地址（Ethereum mainnet）
        self.TOKENS = {
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F"
        }
    
    def execute_trade(self, from_token, to_token, amount, reason=""):
        """执行交易操作"""
        payload = {
            "fromToken": self.TOKENS.get(from_token, from_token),
            "toToken": self.TOKENS.get(to_token, to_token),
            "amount": str(amount),
            "reason": reason or f"Auto trade {from_token}->{to_token}"
        }
        
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30
            )
            return response
        except Exception as e:
            print(f"⚠️ 请求失败: {str(e)}")
            return None
    
    def run(self):
        """主运行循环"""
        print("🚀 Recall 交易代理启动")
        
        while True:
            try:
                # 示例交易：USDC 兑换 WETH
                print("\n📊 执行示例交易...")
                response = self.execute_trade(
                    from_token="USDC",
                    to_token="WETH",
                    amount=100,  # 交易金额
                    reason="快速启动验证交易"
                )
                
                if response and response.status_code == 200:
                    print("✅ 交易成功!")
                    print(f"交易详情: {response.json()}")
                elif response:
                    print(f"❌ 错误 {response.status_code}: {response.text}")
                
                # 每5分钟执行一次
                time.sleep(300)
                
            except KeyboardInterrupt:
                print("\n🛑 代理停止")
                break

if __name__ == "__main__":
    agent = RecallTradingAgent()
    agent.run()