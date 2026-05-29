import type { ChatClient, ChatMessage } from "./types.js";

export class MissingMiniMaxApiKeyError extends Error {
  constructor() {
    super("Missing MiniMax API key. Set MINIMAX_API_KEY, or minimax_api as a fallback.");
    this.name = "MissingMiniMaxApiKeyError";
  }
}

export class MiniMaxHttpError extends Error {
  constructor(
    readonly status: number,
    readonly responseText: string,
  ) {
    super(`MiniMax API returned HTTP ${status}: ${summarize(responseText)}`);
    this.name = "MiniMaxHttpError";
  }
}

export class MiniMaxResponseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MiniMaxResponseError";
  }
}

export type MiniMaxClientOptions = {
  apiKey?: string;
  baseUrl?: string;
  model?: string;
};

export class MiniMaxClient implements ChatClient {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly model: string;

  constructor(options: MiniMaxClientOptions = {}) {
    const apiKey = options.apiKey ?? process.env.MINIMAX_API_KEY ?? process.env.minimax_api;
    if (!apiKey) {
      throw new MissingMiniMaxApiKeyError();
    }

    this.apiKey = apiKey;
    this.baseUrl = (options.baseUrl ?? process.env.MINIMAX_BASE_URL ?? "https://api.minimax.io/v1").replace(/\/$/, "");
    this.model = options.model ?? process.env.MINIMAX_MODEL ?? "MiniMax-M2.7";
  }

  async complete(messages: ChatMessage[]): Promise<string> {
    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        temperature: 0.2,
      }),
    });

    const text = await response.text();
    if (!response.ok) {
      throw new MiniMaxHttpError(response.status, text);
    }

    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw new MiniMaxResponseError(`MiniMax response was not JSON: ${(error as Error).message}`);
    }

    const content = extractContent(data);
    if (!content) {
      throw new MiniMaxResponseError(`MiniMax response did not include choices[0].message.content: ${summarize(text)}`);
    }

    return content;
  }
}

function extractContent(data: unknown): string | undefined {
  if (!isRecord(data)) return undefined;
  const choices = data.choices;
  if (!Array.isArray(choices) || choices.length === 0) return undefined;
  const first = choices[0];
  if (!isRecord(first)) return undefined;
  const message = first.message;
  if (isRecord(message) && typeof message.content === "string") {
    return message.content;
  }
  if (typeof first.text === "string") {
    return first.text;
  }
  return undefined;
}

function summarize(value: string, maxLength = 500): string {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, maxLength)}...`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
