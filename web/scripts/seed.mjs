/**
 * Seed script — populates MongoDB Atlas `hackherway.users` collection.
 * Usage: npm run seed
 * Requires MONGODB_URI in .env (or set in shell).
 */

import { MongoClient } from 'mongodb';
import { config } from 'dotenv';

config({ path: '.env' });

const uri = process.env.MONGODB_URI;
if (!uri) throw new Error('MONGODB_URI is not set. Add it to .env first.');

const USERS = [
  {
    acf2_id: 'RIYA001',
    name: 'Riya Sharma',
    team: 'Payments Backend',
    manager: 'Anjali Singh',
    dept: 'Technology',
    employment_type: 'full-time',
  },
  {
    acf2_id: 'JOHN002',
    name: 'John Mathews',
    team: 'Cloud Infrastructure',
    manager: 'Raj Kumar',
    dept: 'Technology',
    employment_type: 'full-time',
  },
  {
    acf2_id: 'PRIYA003',
    name: 'Priya Nair',
    team: 'Finance Analytics',
    manager: 'Deepa Menon',
    dept: 'Finance',
    employment_type: 'contract',
  },
  {
    acf2_id: 'SAM004',
    name: 'Sam Wilson',
    team: 'TBD',
    manager: 'TBD',
    dept: 'TBD',
    employment_type: 'full-time',
  },
];

async function main() {
  const client = new MongoClient(uri);
  await client.connect();
  console.log('Connected to MongoDB Atlas');

  const db = client.db('hackherway');
  const users = db.collection('users');

  for (const user of USERS) {
    const result = await users.updateOne(
      { acf2_id: user.acf2_id },
      { $set: user },
      { upsert: true },
    );
    const action = result.upsertedCount ? 'inserted' : 'updated';
    console.log(`  ${action}: ${user.acf2_id} — ${user.name}`);
  }

  await users.createIndex({ acf2_id: 1 }, { unique: true });
  console.log('Index ensured: acf2_id (unique)');

  await client.close();
  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
