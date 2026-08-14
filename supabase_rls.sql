-- 允許 anon 角色操作 guild_config 表格
ALTER TABLE guild_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_guild_config" ON guild_config
    FOR ALL USING (true) WITH CHECK (true);

-- 允許 anon 角色操作 players 表格
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_players" ON players
    FOR ALL USING (true) WITH CHECK (true);

-- 允許 anon 角色操作 snipers 表格
ALTER TABLE snipers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_snipers" ON snipers
    FOR ALL USING (true) WITH CHECK (true);
