import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH =
  process.env.SQLITE_DB_PATH ?? path.join(process.cwd(), 'hackherway.db');

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!_db) {
    _db = new Database(DB_PATH);
    _db.pragma('journal_mode = WAL');
    initSchema(_db);
  }
  return _db;
}

function initSchema(db: Database.Database) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      acf2_id          TEXT PRIMARY KEY,
      name             TEXT NOT NULL,
      team             TEXT,
      manager          TEXT,
      dept             TEXT,
      employment_type  TEXT
    );

    CREATE TABLE IF NOT EXISTS conversations (
      id          TEXT PRIMARY KEY,
      acf2_id     TEXT NOT NULL,
      created_at  INTEGER NOT NULL,
      updated_at  INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS messages (
      id               TEXT PRIMARY KEY,
      conversation_id  TEXT NOT NULL,
      role             TEXT NOT NULL CHECK(role IN ('user', 'bot')),
      content          TEXT NOT NULL,
      created_at       INTEGER NOT NULL,
      FOREIGN KEY(conversation_id) REFERENCES conversations(id)
    );

    CREATE TABLE IF NOT EXISTS ritm_requests (
      id               TEXT PRIMARY KEY,
      acf2_id          TEXT NOT NULL,
      conversation_id  TEXT,
      template_id      TEXT,
      status           TEXT DEFAULT 'pending',
      snow_request_id  TEXT,
      created_at       INTEGER NOT NULL
    );
  `);
}
