import {
  BedrockRuntimeClient,
  ConverseCommand,
  type Message as BedrockMessage,
} from '@aws-sdk/client-bedrock-runtime';

let _client: BedrockRuntimeClient | null = null;

function getClient(): BedrockRuntimeClient {
  if (!_client) {
    _client = new BedrockRuntimeClient({
      region: process.env.AWS_REGION ?? 'us-east-1',
      credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
        ...(process.env.AWS_SESSION_TOKEN && {
          sessionToken: process.env.AWS_SESSION_TOKEN,
        }),
      },
    });
  }
  return _client;
}

const MODEL_ID: string =
  process.env.BEDROCK_MODEL_ID ?? 'us.anthropic.claude-sonnet-4-6-20250514-v1:0';

export async function converse(
  systemPrompt: string,
  messages: BedrockMessage[],
): Promise<string> {
  const command = new ConverseCommand({
    modelId: MODEL_ID,
    system: [{ text: systemPrompt }],
    messages,
    inferenceConfig: {
      maxTokens: 512,
      temperature: 0.7,
    },
  });

  const response = await getClient().send(command);
  const content = response.output?.message?.content?.[0];
  if (content && 'text' in content && content.text) return content.text;
  throw new Error('No text output from Bedrock');
}
