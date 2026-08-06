-- 建立 guild_config 資料表
CREATE TABLE guild_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    guild_id TEXT UNIQUE NOT NULL,
    channel_id TEXT,
    players JSONB DEFAULT '{}'::jsonb
);

-- 建立索引加速查詢
CREATE INDEX idx_guild_config_guild_id ON guild_config(guild_id);

-- 插入你的伺服器測試資料（可選）
INSERT INTO guild_config (guild_id, channel_id, players)
VALUES (
    '1042829407359864882',
    NULL,
    '{"Lun": "23011282", "Player2": "4006652", "Player3": "25291306", "Player4": "25365314", "Player5": "24745104", "Player6": "18387129", "Player7": "22928375", "Player8": "23726824", "Player9": "23640436", "Player10": "21249015"}'::jsonb
)
ON CONFLICT (guild_id) DO NOTHING;
