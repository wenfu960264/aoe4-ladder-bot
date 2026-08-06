import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
import json
import os
import datetime
import threading
from flask import Flask
from supabase import create_client, Client

# ---- Supabase 連線 ----
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- 健康檢查端點（供 UptimeRobot ping） ----
app = Flask(__name__)

@app.route("/")
def health():
    return "OK"

def run_web():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_web, daemon=True).start()

# ---- 設定 ----
AUTO_SEND_TIME = datetime.time(hour=18, minute=0, second=0)

# ---- Bot ----
class AoE4Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        print("同步斜線指令")
        await self.tree.sync()
        print("斜線成功！")
        self.daily_leaderboard_loop.start()
        print("每日定時發送成功")

    @tasks.loop(time=AUTO_SEND_TIME)
    async def daily_leaderboard_loop(self):
        print("🕒 定時觸發：正在為各個伺服器生成詳細排行榜...")
        db = load_db()

        for guild_id_str, config in db.items():
            channel_id = config.get("channel_id")
            if not channel_id:
                continue

            channel = self.get_channel(int(channel_id))
            if not channel:
                print(f"❌ 伺服器 {guild_id_str} 找不到指定的頻道 ID: {channel_id}")
                continue

            players_dict = config.get("players", {})
            if not players_dict:
                continue

            content_solo = await fetch_detailed_leaderboard(players_dict, mode_type="rm_solo")
            if content_solo:
                await channel.send(content=f"📢 **【單人排位】**\n{content_solo}")

            content_team = await fetch_detailed_leaderboard(players_dict, mode_type="rm_team")
            if content_team:
                await channel.send(content=f"📢 **【團隊排位】**\n{content_team}")

bot = AoE4Bot()

# ---- Supabase 讀寫 ----
def load_db():
    response = supabase.table("guild_config").select("*").execute()
    db = {}
    for row in response.data:
        db[row["guild_id"]] = {
            "channel_id": row["channel_id"],
            "players": row["players"] or {}
        }
    return db

def save_db(data):
    for guild_id, config in data.items():
        supabase.table("guild_config").upsert({
            "guild_id": guild_id,
            "channel_id": config["channel_id"],
            "players": config["players"]
        }).execute()

# ---- 文明 / 排位翻譯 ----
CIV_MAPPING = {
    "byzantines": "拜占庭",
    "holy_roman_empire": "神聖羅馬帝國",
    "delhi_sultanate": "德里",
    "french": "法蘭西",
    "malians": "馬利",
    "order_of_the_dragon": "龍騎士團",
    "abbasid_dynasty": "阿拔斯",
    "english": "英格蘭",
    "mongols": "蒙古",
    "ayyubids": "阿育布",
    "ottomans": "鄂圖曼",
    "rus": "羅斯",
    "jeanne_darc": "貞德",
    "japanese": "日本",
    "chinese": "中國",
    "zhu_xis_legacy": "朱熹",
    "knights_templar": "聖殿騎士團",
    "house_of_lancaster": "蘭卡斯特",
    "macedonian_dynasty": "馬其頓王朝",
    "golden_horde": "金帳汗國",
    "tughlaq_dynasty": "圖格魯克王朝",
    "sengoku_daimyo": "大名",
    "jin_dynasty": "金朝",
}

RANK_MAPPING = {
    "conqueror_3": "征服者3", "conqueror_2": "征服者2", "conqueror_1": "征服者1",
    "diamond_3": "鑽石3", "diamond_2": "鑽石2", "diamond_1": "鑽石1",
    "platinum_3": "白金3", "platinum_2": "白金2", "platinum_1": "白金1",
    "gold": "黃金3", "gold_2": "黃金2", "gold_1": "黃金1",
    "silver": "白銀3", "silver_2": "白銀2", "silver_1": "白銀",
    "bronze_3": "青銅3", "bronze_2": "青銅2", "bronze_1": "青銅1",
}

def translate_civ(civ_name):
    if not civ_name:
        return "未知"
    return CIV_MAPPING.get(civ_name.lower(), civ_name.title())

def translate_rank(rank_level):
    if not rank_level:
        return "未知"
    return RANK_MAPPING.get(rank_level.lower(), rank_level.title())

# ---- 排行榜核心邏輯 ----
async def fetch_detailed_leaderboard(players_dict, mode_type="rm_solo"):
    if not players_dict:
        return None

    leaderboard_data = []

    for custom_name, aoe4_id in players_dict.items():
        api_url = f"https://aoe4world.com/api/v0/players/{aoe4_id}"
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                player_name = data.get("name", custom_name)

                modes = data.get("modes", {})
                target_mode = modes.get(mode_type, {}) if modes else {}

                if target_mode:
                    rating = target_mode.get("rating", 0)
                    max_rating = target_mode.get("max_rating", 0)
                    rank_level = target_mode.get("rank_level", "Unranked")
                    rank = target_mode.get("rank", "無")
                    games = target_mode.get("games_count", 0)
                    win_rate = target_mode.get("win_rate", 0)
                else:
                    rating, max_rating, games, win_rate = 0, 0, 0, 0
                    rank_level, rank = "Unranked", "無"

                favorite_civ = "未知"
                civ_play_rate = 0
                civ_data = target_mode.get("civilizations", []) if target_mode else []
                if not civ_data and modes:
                    for m in modes.values():
                        if m.get("civilizations"):
                            civ_data = m["civilizations"]
                            break
                if civ_data:
                    sorted_civs = sorted(civ_data, key=lambda x: x.get("games_count", 0), reverse=True)
                    if sorted_civs:
                        favorite_civ = translate_civ(sorted_civs[0].get("civilization"))
                        total_civ_games = sum(c.get("games_count", 0) for c in civ_data)
                        if total_civ_games > 0:
                            civ_play_rate = int((sorted_civs[0].get("games_count", 0) / total_civ_games) * 100)

                last_game_str = data.get("last_game_at")
                days_ago_str = "未知"
                if last_game_str:
                    try:
                        last_game_time = datetime.datetime.fromisoformat(last_game_str.replace("Z", "+00:00"))
                        now = datetime.datetime.now(datetime.timezone.utc)
                        delta = now - last_game_time
                        days_ago_str = f"{delta.days}天前" if delta.days > 0 else "今天"
                    except Exception:
                        pass

                leaderboard_data.append({
                    "discord_name": custom_name,
                    "name": player_name,
                    "aoe4_id": aoe4_id,
                    "rating": rating,
                    "max_rating": max_rating,
                    "rank_level": rank_level,
                    "rank": rank,
                    "games": games,
                    "win_rate": int(win_rate) if win_rate else 0,
                    "civ": favorite_civ,
                    "civ_rate": civ_play_rate,
                    "days_ago": days_ago_str,
                })
        except Exception as e:
            print(f"撈取玩家 {aoe4_id} 資料時發生異常: {e}")

    leaderboard_data.sort(key=lambda x: x["rating"], reverse=True)

    output_text = ""
    for index, p in enumerate(leaderboard_data, start=1):
        output_text += f"第{index}名  **{p['discord_name']}**\n"
        output_text += f"遊戲ID [{p['name']}](https://aoe4world.com/players/{p['aoe4_id']})\n"
        output_text += f"**{translate_rank(p['rank_level'])}**  ({p['rating']})\n"
        output_text += f"全球排名: {p['rank']}，遊戲場次: {p['games']} (勝率: {p['win_rate']}%)\n"
        output_text += f"愛用文明: {p['civ']}，出場率 {p['civ_rate']}%\n\n"
    return output_text

# ---- 事件 ----
@bot.event
async def on_ready():
    print(f"機器人已成功上線！目前登入為：{bot.user}")

# ---- /綁定 ----
@bot.tree.command(name="綁定", description="綁定您的 AoE4 World ID 至此 Discord 伺服器")
@app_commands.describe(aoe4_id="請輸入您在 AoE4 World 的純數字 ID")
async def register(interaction: discord.Interaction, aoe4_id: str):
    await interaction.response.defer(ephemeral=True)

    guild_id = str(interaction.guild_id)
    api_url = f"https://aoe4world.com/api/v0/players/{aoe4_id}"
    response = requests.get(api_url)

    if response.status_code != 200:
        await interaction.followup.send(f" 找不到 AoE4 World ID: `{aoe4_id}`，請檢查數字是否正確！")
        return

    player_name = response.json().get("name", "未知玩家")

    db = load_db()
    if guild_id not in db:
        db[guild_id] = {"channel_id": None, "players": {}}

    db[guild_id]["players"][interaction.user.display_name] = aoe4_id
    save_db(db)

    await interaction.followup.send(
        f"✅ 成功將 **{interaction.user.mention}** 綁定至本伺服器天梯名冊：**{player_name}** (ID: {aoe4_id})"
    )

# ---- /設定通知頻道 ----
@bot.tree.command(name="設定通知頻道", description="設定此伺服器每日自動發送排行榜的文字頻道")
@app_commands.checks.has_permissions(manage_channels=True)
async def set_channel(interaction: discord.Interaction, 頻道: discord.TextChannel):
    guild_id = str(interaction.guild_id)
    db = load_db()

    if guild_id not in db:
        db[guild_id] = {"channel_id": None, "players": {}}

    db[guild_id]["channel_id"] = 頻道.id
    save_db(db)

    await interaction.response.send_message(f"成功將每日自動發送排行榜的頻道設定為：{頻道.mention}")

# ---- /排行榜 ----
@bot.tree.command(name="排行榜", description="顯示目前伺服器已綁定玩家的排位分數詳細排行榜")
@app_commands.choices(模式=[
    app_commands.Choice(name="單人排位 (RM Solo)", value="rm_solo"),
    app_commands.Choice(name="團隊排位 (RM Team)", value="rm_team"),
])
@app_commands.describe(模式="請選擇您要查詢的排位模式（預設為單人排位）")
async def leaderboard(interaction: discord.Interaction, 模式: app_commands.Choice[str] = None):
    await interaction.response.defer()

    guild_id = str(interaction.guild_id)
    db = load_db()

    if guild_id not in db or not db[guild_id].get("players"):
        await interaction.followup.send("ℹ️ 目前本伺服器尚未有任何玩家綁定資料。請使用 `/綁定`！")
        return

    selected_mode = 模式.value if 模式 else "rm_solo"
    mode_title = "單人排位" if selected_mode == "rm_solo" else "團隊排位"

    players_dict = db[guild_id]["players"]
    content = await fetch_detailed_leaderboard(players_dict, mode_type=selected_mode)

    if content:
        heading = f" **{mode_title}天梯榜** \n\n"
        await interaction.followup.send(f"{heading}\n{content}")
    else:
        await interaction.followup.send("ℹ️ 本伺服器綁定的玩家目前無天梯分數數據。")

# ---- /狙擊手 ----
@bot.tree.command(name="狙擊手", description="列出伺服器所有狙擊手（已綁定玩家）的單排詳細資料")
async def snipers(interaction: discord.Interaction):
    await interaction.response.defer()

    guild_id = str(interaction.guild_id)
    db = load_db()

    if guild_id not in db or not db[guild_id].get("players"):
        await interaction.followup.send("ℹ️ 目前本伺服器尚未有任何狙擊手資料。")
        return

    players_dict = db[guild_id]["players"]
    content = await fetch_detailed_leaderboard(players_dict, mode_type="rm_solo")

    if content:
        heading = " **狙擊手天梯榜（單排）**\n\n"
        await interaction.followup.send(f"{heading}\n{content}")
    else:
        await interaction.followup.send("ℹ️ 本伺服器狙擊手目前無天梯分數數據。")

# ---- 啟動 ----
bot.run(os.getenv("DISCORD_TOKEN"))
