import { Router, Request, Response } from 'express';
import { getDb } from '../lib/sqlite';

const router = Router();

router.get('/', (req: Request, res: Response) => {
  const acf2_id = (req.query.acf2_id as string)?.toUpperCase();

  if (!acf2_id) {
    return res.status(400).json({ error: 'acf2_id query param required' });
  }

  try {
    const db = getDb();
    const conversations = db
      .prepare(
        `SELECT id, acf2_id, created_at, updated_at
         FROM conversations
         WHERE acf2_id = ?
         ORDER BY updated_at DESC
         LIMIT 20`,
      )
      .all(acf2_id);

    return res.json({ conversations });
  } catch (err) {
    console.error('[GET /api/conversations]', err);
    return res.json({ conversations: [] });
  }
});

export default router;
