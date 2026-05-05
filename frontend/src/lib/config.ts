export const config = {
  backendUrl: process.env.BACKEND_URL ?? 'http://localhost:8000',
  publicBaseUrl: process.env.PUBLIC_BASE_URL ?? 'http://localhost:3000',
} as const;
