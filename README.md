# Donbotto

Donbotto is a retro-styled concept app for **free LLM desktop automation** on Linux.

## Concept

Instead of forcing an AI agent to output rigid JSON actions, Donbotto demonstrates a direct runtime loop:

1. A local/open model interprets your goal.
2. It decides the next immediate UI action.
3. Donbotto runs the action with `xdotool` in real time.
4. It checks state and continues until complete.

## Why this approach

- No paid API requirement (works with local models).
- Real desktop control via native Linux automation tools.
- Fast loop for practical tasks (open apps, type, click, switch windows).

## Run

Open `index.html` in a browser.
