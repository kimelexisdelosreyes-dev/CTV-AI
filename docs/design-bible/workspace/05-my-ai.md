# 05 - My AI Briefing

## Purpose

My AI is a daily assistant, not a chatbot. It summarizes useful context and suggests timely assistance.

## Topics

- Overnight work.
- Completed AI jobs.
- Recommended documents.
- Approvals.
- Deadlines.
- Project reminders.
- Context-aware suggestions.

## Information Priority

1. Requires user action.
2. Completed work ready for review.
3. Deadline or meeting relevance.
4. Knowledge recommendation.
5. Optional improvement suggestion.

## Tone

Calm, brief, specific:

- "Subtitle generation finished for Fire Documentary. Review 12 flagged lines."
- "The campaign deck is missing approved pricing language."
- "Three policy updates may affect today's HR response."

Avoid:

- Chatty greetings.
- Overconfident claims.
- Technical AI process language.
- Long paragraphs.

## Content Limits

- Maximum three briefing items by default.
- Each item: one sentence plus one action.
- Expand reveals source, reason, and secondary action.

## Behavior

- Dismiss hides the item for the current context.
- Important compliance or approval items cannot be permanently dismissed without action.
- My AI should not interrupt work with unsolicited modal prompts.
- My AI can recommend actions but should not auto-change work.

## Expandable Anatomy

```text
+------------------------------------------------+
| My AI Briefing                                 |
| Subtitle generation finished. [Review]         |
| Campaign proposal needs approved tagline. [Open]|
| HR policy update is recommended reading. [Read]|
|                                                |
| [Show details]                                 |
+------------------------------------------------+
```

