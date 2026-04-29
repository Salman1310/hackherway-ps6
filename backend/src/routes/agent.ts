import { Router, Request, Response } from 'express';
import { handleAgentMessage } from '../agent/index';
import type { SessionState, ChatMessage } from '../types';

const router = Router();

router.post('/message', async (req: Request, res: Response) => {
  try {
    const { content, session, history } = req.body as {
      content: string;
      session: SessionState;
      history: ChatMessage[];
    };

    if (!content?.trim()) {
      return res.status(400).json({ reply: 'Message content is required.' });
    }

    const result = await handleAgentMessage(content, session, history ?? []);
    return res.json(result);
  } catch (err) {
    console.error('[POST /api/agent/message]', err);
    return res.status(500).json({ reply: 'Something went wrong on my end. Please try again.' });
  }
});

export default router;
