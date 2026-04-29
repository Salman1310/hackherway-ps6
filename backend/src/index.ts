import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

import agentRouter from './routes/agent';
import conversationsRouter from './routes/conversations';

const app = express();
const PORT = Number(process.env.PORT ?? 8000);

// Allow requests from the Next.js frontend (any local network IP)
app.use(
  cors({
    origin: (origin, cb) => {
      // Allow requests with no origin (curl, server-to-server) and localhost/LAN
      if (!origin || /^http:\/\/(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+)(:\d+)?$/.test(origin)) {
        return cb(null, true);
      }
      cb(new Error(`CORS blocked: ${origin}`));
    },
  }),
);

app.use(express.json());

// Routes
app.use('/api/agent', agentRouter);
app.use('/api/conversations', conversationsRouter);

// Health check
app.get('/health', (_req, res) => res.json({ status: 'ok', ts: Date.now() }));

app.listen(PORT, () => {
  console.log(`\nBackend running on http://localhost:${PORT}`);
  console.log(`  Health: http://localhost:${PORT}/health\n`);
});
