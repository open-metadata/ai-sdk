/**
 * SSE streaming parser for the Metadata AI SDK.
 *
 * This module provides utilities for parsing Server-Sent Events (SSE)
 * from streaming agent responses.
 */

import type { StreamEvent, StreamEventType } from './models.js';

/**
 * Map SSE event type names to StreamEvent types.
 */
function mapEventType(eventType: string | null): StreamEventType {
  if (!eventType) {
    return 'content';
  }

  const typeMapping: Record<string, StreamEventType> = {
    'stream-start': 'start',
    message: 'content',
    'tool-use': 'tool_use',
    'stream-completed': 'end',
    error: 'error',
    'fatal-error': 'error',
  };

  return typeMapping[eventType] || (eventType as StreamEventType);
}

/**
 * Parse a single SSE event string into a StreamEvent.
 */
function parseEvent(eventStr: string): StreamEvent | null {
  let eventType: string | null = null;
  let data: string | null = null;

  for (const line of eventStr.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('event:')) {
      eventType = trimmed.slice(6).trim();
    } else if (trimmed.startsWith('data:')) {
      data = trimmed.slice(5).trim();
    }
    // 'id:' lines are currently not used
  }

  if (!data) {
    return null;
  }

  // Parse JSON data
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(data) as Record<string, unknown>;
  } catch {
    // If not valid JSON, treat as plain text content
    payload = { content: data };
  }

  const mappedType = mapEventType(eventType);

  // Extract content from the nested message structure
  // The API returns: {"data": {"message": {"content": [{"textMessage": {"message": "..."}}]}}}
  let content: string | undefined;
  let toolName: string | undefined;
  let conversationId = payload.conversationId as string | undefined;

  const dataField = payload.data as Record<string, unknown> | undefined;
  if (dataField?.message) {
    const message = dataField.message as Record<string, unknown>;
    // Get conversation ID from message if not at top level
    if (!conversationId) {
      conversationId = message.conversationId as string | undefined;
    }
    // Extract text content from content blocks
    const contentBlocks = message.content as Array<Record<string, unknown>> | undefined;
    if (contentBlocks && Array.isArray(contentBlocks)) {
      const textParts: string[] = [];
      for (const block of contentBlocks) {
        // Extract text message
        const textMessage = block.textMessage as Record<string, unknown> | string | undefined;
        if (textMessage) {
          if (typeof textMessage === 'object' && textMessage.message) {
            textParts.push(textMessage.message as string);
          } else if (typeof textMessage === 'string') {
            textParts.push(textMessage);
          }
        }
        // Extract tool names
        const tools = block.tools as Array<Record<string, unknown>> | undefined;
        if (tools && Array.isArray(tools)) {
          for (const tool of tools) {
            if (tool.name) {
              toolName = tool.name as string;
            }
          }
        }
      }
      if (textParts.length > 0) {
        content = textParts.join('');
      }
    }
  } else if (payload.content) {
    // Fallback to direct content field
    content = payload.content as string;
  }

  return {
    type: mappedType,
    content,
    toolName,
    conversationId,
    error: mappedType === 'error' ? ((payload.error as string | undefined) || (payload.message as string | undefined)) : undefined,
  };
}

/**
 * Async generator that parses SSE events from a ReadableStream.
 *
 * @param stream - The ReadableStream of bytes from the HTTP response
 * @yields StreamEvent objects as they are parsed
 */
export async function* parseSSEStream(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<StreamEvent, void, unknown> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        // Process any remaining buffer content
        if (buffer.trim()) {
          const event = parseEvent(buffer);
          if (event) {
            yield event;
          }
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete events (delimited by double newlines)
      while (buffer.includes('\n\n')) {
        const [eventStr, rest] = buffer.split('\n\n', 2);
        buffer = rest;

        const event = parseEvent(eventStr);
        if (event) {
          yield event;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Create an async iterable from a streaming response.
 *
 * This is a convenience wrapper that allows using the stream with `for await...of`.
 *
 * @param stream - The ReadableStream of bytes from the HTTP response
 * @returns An async iterable of StreamEvent objects
 *
 * @example
 * ```typescript
 * const stream = await httpClient.postStream('/agent/stream', body);
 * for await (const event of createStreamIterable(stream)) {
 *   if (event.type === 'content') {
 *     process.stdout.write(event.content || '');
 *   }
 * }
 * ```
 */
export function createStreamIterable(
  stream: ReadableStream<Uint8Array>
): AsyncIterable<StreamEvent> {
  return {
    [Symbol.asyncIterator]() {
      return parseSSEStream(stream);
    },
  };
}
