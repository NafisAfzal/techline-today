# Demo recording

Record a 60-second browser walkthrough from a fresh live edition. A screen recording is more useful than generated video because it shows the actual source and browser interactions. Keep the video outside Git; there is no music or voiceover requirement.

```powershell
py -3.12 -m uv run python -m pipeline --mode live
pnpm.cmd build
pnpm.cmd preview
```

Use Chromium at 1280 × 900, light theme, 100% zoom. Record only the browser content at http://127.0.0.1:4321. Close unrelated tabs and disable notifications. If port 4321 already hosts a development server, stop it first or choose another preview port with `PORT`.

| Seconds | Action |
|---|---|
| 0–8 | Homepage: pause on the lead and its evidence label. |
| 8–16 | Scroll to the four briefing items, then the category index. |
| 16–23 | Open AI or Chips. Pause on a headline and labelled facts. |
| 23–34 | Open Details; show the summary, citations and source panel. Do not expand a long publisher excerpt. |
| 34–42 | Open search with `/`, search a model/tool present in this edition, then use Escape. |
| 42–50 | Save the story; open Saved and show the local reading list. |
| 50–55 | Preferences: select a category and show the saved confirmation. |
| 55–65 | Open a digest or Free credit and finish on the official terms link. |

Review the result for legible text, smooth scrolling and clear pauses. Export MP4 or WebM into `.cache/demo/`, upload it separately if desired, and link it only after it exists. Never commit a large recording or claim the preview is deployed. The repository includes still captures; no video was produced during this pass.

After recording, regenerate fixture mode and rebuild before E2E tests.
