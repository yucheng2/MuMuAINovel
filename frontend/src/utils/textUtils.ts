/**
 * Strip thinking blocks from text
 */
export function stripThinkingBlocks(text: string): string {
  if (!text) return text;
  const pattern = new RegExp('<think>[\\s\\S]*?</think>', 'g');
  return text.replace(pattern, '').trim();
}
