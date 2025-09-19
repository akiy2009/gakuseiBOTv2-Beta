# config.py - セキュア設定管理
"""
gakuseiBOT セキュア設定管理システム
環境変数を優先し、フォールバック値を提供します。

使用方法:
from .config import BotConfig
config = BotConfig()
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# セキュリティ警告用のデフォルト値
DEFAULT_PLACEHOLDER = "NOT_SET_PLEASE_CONFIGURE"

class BotConfig:
    """Bot設定クラス - セキュアな設定管理"""
    
    def __init__(self):
        # 必須設定（セキュリティ警告付き）
        self.DEVELOPER_ID: Optional[int] = self._get_int_env('DEVELOPER_ID', warn_if_default=True)
        self.FEEDBACK_CHANNEL_ID: Optional[int] = self._get_int_env('FEEDBACK_CHANNEL_ID', warn_if_default=True)
        self.REPORT_CHANNEL_ID: Optional[int] = self._get_int_env('REPORT_CHANNEL_ID', warn_if_default=True)
        
        # サイト関連（環境変数優先）
        self.OFFICIAL_WEBSITE: str = os.getenv('OFFICIAL_WEBSITE', 'https://gakuseibot.com')
        self.DASHBOARD_URL: str = os.getenv('DASHBOARD_URL', 'https://dashboard.gakuseibot.com')
        
        # GitHub関連
        self.GITHUB_REPO: str = os.getenv('GITHUB_REPO', 'https://github.com/akiy2009/gakuseiBOTv2-Beta')
        
        # Discord関連
        self.SUPPORT_SERVER_INVITE: str = os.getenv('SUPPORT_SERVER_INVITE', 'https://discord.gg/9x3FwmPxhP')
        
        # セキュリティ設定
        self.DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
        self.LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
        
    def _get_int_env(self, key: str, default: Optional[int] = None, warn_if_default: bool = False) -> Optional[int]:
        """環境変数から整数値を取得（セキュリティ警告付き）"""
        value = os.getenv(key)
        if value is None:
            if warn_if_default and default is None:
                logger.warning(f"⚠️ {key} が環境変数に設定されていません。セキュリティ上の理由でデフォルト値は使用しません。")
                return None
            return default
        try:
            return int(value)
        except ValueError:
            logger.error(f"❌ {key} の値が無効です: {value}")
            return default
    
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