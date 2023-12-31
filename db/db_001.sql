-- SQLite
CREATE TABLE IF NOT EXISTS channels_types(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) NOT NULL
);
CREATE TABLE IF NOT EXISTS channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    guild_name VARCHAR(64) NOT NULL,
    channel_type INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    channel_name VARCHAR(64) NOT NULL,
    CONSTRAINT fk_channels_channel_type 
        FOREIGN KEY(channel_type) 
        REFERENCES channels_types(id)
);

INSERT INTO channels_types(name) VALUES('announce');
INSERT INTO channels_types(name) VALUES('report');
INSERT INTO channels_types(name) VALUES('observe');
