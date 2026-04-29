export const config = {
  bypassAuth: process.env.BYPASS_AUTH === 'true',
  mongodbUri: process.env.MONGODB_URI ?? 'mongodb://localhost:27017/hackherway',
  awsRegion: process.env.AWS_REGION ?? 'us-east-1',
  teamsWebhookUrl: process.env.TEAMS_WEBHOOK_URL ?? '',
  publicBaseUrl: process.env.PUBLIC_BASE_URL ?? 'http://localhost:3000',
} as const;
