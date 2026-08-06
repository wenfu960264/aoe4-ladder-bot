-- =============================================
-- AoE4 Discord Bot 資料庫設定
-- 三個表格：guild_config、players、snipers
-- =============================================

-- 1. 伺服器設定表
CREATE TABLE IF NOT EXISTS guild_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    guild_id TEXT UNIQUE NOT NULL,
    channel_id TEXT
);

-- 2. 綁定玩家表（單排/團戰用，由 /綁定 新增）
CREATE TABLE IF NOT EXISTS players (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    guild_id TEXT NOT NULL,
    discord_name TEXT NOT NULL,
    aoe4_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (guild_id, discord_name)
);

-- 3. 狙擊手表（手動管理）
CREATE TABLE IF NOT EXISTS snipers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    guild_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    aoe4_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (guild_id, display_name)
);

-- =============================================
-- 索引
-- =============================================
CREATE INDEX IF NOT EXISTS idx_players_guild ON players(guild_id);
CREATE INDEX IF NOT EXISTS idx_snipers_guild ON snipers(guild_id);
CREATE INDEX IF NOT EXISTS idx_guild_config_guild ON guild_config(guild_id);

-- =============================================
-- 測試資料（可選）
-- 你的伺服器 ID：1042829407359864882
-- =============================================

-- 伺服器設定
INSERT INTO guild_config (guild_id, channel_id)
VALUES ('1042829407359864882', NULL)
ON CONFLICT (guild_id) DO NOTHING;

-- 綁定玩家（單排/團戰用）
INSERT INTO players (guild_id, discord_name, aoe4_id) VALUES
    ('1042829407359864882', 'Lun', '23011282')
ON CONFLICT (guild_id, discord_name) DO NOTHING;

-- 狙擊手（手動管理）
INSERT INTO snipers (guild_id, display_name, aoe4_id) VALUES
    ('1042829407359864882', 'Lun', '23011282'),
    ('1042829407359864882', 'Player2', '4006652'),
    ('1042829407359864882', 'Player3', '25291306'),
    ('1042829407359864882', 'Player4', '25365314'),
    ('1042829407359864882', 'Player5', '24745104'),
    ('1042829407359864882', 'Player6', '18387129'),
    ('1042829407359864882', 'Player7', '22928375'),
    ('1042829407359864882', 'Player8', '23726824'),
    ('1042829407359864882', 'Player9', '23640436'),
    ('1042829407359864882', 'Player10', '21249015')
ON CONFLICT (guild_id, display_name) DO NOTHING;
