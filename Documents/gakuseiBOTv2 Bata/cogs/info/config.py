# config.py - 設定ファイル
"""
gakuseiBOT設定ファイル
ハードコードされた値を一元管理します。

使用方法:
from .config import BotConfig
config = BotConfig()
"""

import os
from typing import Optional


class BotConfig:
    """Bot設定クラス"""
    
    def __init__(self):
        # 環境変数から取得、なければデフォルト値
        self.DEVELOPER_ID: int = int(os.getenv('DEVELOPER_ID', '1241366063858450485'))
        self.FEEDBACK_CHANNEL_ID: int = int(os.getenv('FEEDBACK_CHANNEL_ID', '1301185017619415092'))
        self.REPORT_CHANNEL_ID: int = int(os.getenv('REPORT_CHANNEL_ID', '1291296590950301753'))
        
        # サイト関連
        self.OFFICIAL_WEBSITE: str = os.getenv('OFFICIAL_WEBSITE', 'https://gakuseibot.com')
        self.DASHBOARD_URL: str = os.getenv('DASHBOARD_URL', 'https://dashboard.gakuseibot.com')
        
        # GitHub関連
        self.GITHUB_REPO: str = os.getenv('GITHUB_REPO', 'https://github.com/akiy2009/gakuseiBOTv2-Beta')
        
        # Discord関連
        self.SUPPORT_SERVER_INVITE: str = os.getenv('SUPPORT_SERVER_INVITE', 'https://discord.gg/9x3FwmPxhP')
    
    def is_developer(self, user_id: int) -> bool:
        """指定されたユーザーIDが開発者かどうかを確認"""
        return user_id == self.DEVELOPER_ID
    
    def get_channel_id(self, channel_type: str) -> Optional[int]:
        """チャンネルタイプに応じたチャンネルIDを取得"""
        channel_map = {
            'feedback': self.FEEDBACK_CHANNEL_ID,
            'report': self.REPORT_CHANNEL_ID
        }
        return channel_map.get(channel_type.lower())


# グローバル設定インスタンス
bot_config = BotConfig()