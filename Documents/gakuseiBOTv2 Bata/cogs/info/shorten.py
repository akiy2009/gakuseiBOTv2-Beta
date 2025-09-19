import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import re
import ipaddress
from urllib.parse import urlparse, quote
import socket

class URLShortener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # ブロックするドメイン/サフィックス
        self.blocked_domains = {
            'localhost', '127.0.0.1', '0.0.0.0',
            'malware.com', 'phishing.com', 'spam.com'  # 例
        }
        # ブロックするプライベートIPレンジ
        self.private_ranges = [
            ipaddress.IPv4Network('10.0.0.0/8'),
            ipaddress.IPv4Network('172.16.0.0/12'),
            ipaddress.IPv4Network('192.168.0.0/16'),
            ipaddress.IPv4Network('169.254.0.0/16'),  # リンクローカル
            ipaddress.IPv4Network('127.0.0.0/8'),     # ループバック
        ]

    def _is_safe_url(self, url: str) -> tuple[bool, str]:
        """
        URLの安全性をチェックする
        Returns: (is_safe, error_message)
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or parsed.scheme not in ['http', 'https']:
                return False, "サポートされていないプロトコルです"
            
            hostname = parsed.hostname
            if not hostname:
                return False, "無効なURL形式です"
            
            # ブロックドメインチェック
            if hostname.lower() in self.blocked_domains:
                return False, "ブロックされたドメインです"
            
            # IPアドレスチェック
            try:
                ip = ipaddress.IPv4Address(hostname)
                # プライベートIPチェック
                for private_range in self.private_ranges:
                    if ip in private_range:
                        return False, "プライベートIPアドレスは使用できません"
            except ipaddress.AddressValueError:
                # ドメイン名の場合はスキップ
                pass
            
            return True, ""
        except Exception:
            return False, "URLの解析に失敗しました"
    
    @app_commands.command(name="shorten", description="URLを安全に短縮します")
    @app_commands.describe(url="短縮したいURLを入力してください")
    async def shorten(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        
        # URLのサニタイズと正規化
        url = url.strip()
        if not re.match(r'^https?://', url):
            url = 'https://' + url
        
        # セキュリティチェック
        is_safe, error_msg = self._is_safe_url(url)
        if not is_safe:
            await interaction.followup.send(f"⚠️ セキュリティエラー: {error_msg}", ephemeral=True)
            return
        
        # URLの長さチェック
        if len(url) > 2000:
            await interaction.followup.send("⚠️ URLが長すぎます。", ephemeral=True)
            return

        try:
            # URLエンコードしてAPIリクエストを作成
            encoded_url = quote(url, safe=':/?#[]@!$&\'()*+,;=')
            api_url = f"https://is.gd/create.php?format=simple&url={encoded_url}"
            
            # タイムアウトとレートリミットを設定
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        short_url = await resp.text()
                        short_url = short_url.strip()
                        
                        # レスポンスのバリデーション
                        if short_url.startswith('http'):
                            embed = discord.Embed(
                                title="🔗 URL短縮完了",
                                description=f"**元URL**: {url[:100]}{'...' if len(url) > 100 else ''}\n**短縮URL**: {short_url}",
                                color=discord.Color.green()
                            )
                            await interaction.followup.send(embed=embed)
                        else:
                            # エラーメッセージの場合
                            await interaction.followup.send(f"⚠️ URL短縮サービスエラー: 無効なURLまたはサービスエラーです", ephemeral=True)
                    else:
                        await interaction.followup.send(f"⚠️ URL短縮サービスエラー (HTTP {resp.status})", ephemeral=True)
                        
        except aiohttp.ClientError:
            await interaction.followup.send("⚠️ ネットワークエラーが発生しました。", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("⚠️ タイムアウトしました。しばらく待ってから再度試してください。", ephemeral=True)
        except Exception:
            # 詳細なエラー情報を隐す
            await interaction.followup.send("⚠️ 予期しないエラーが発生しました。", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(URLShortener(bot))