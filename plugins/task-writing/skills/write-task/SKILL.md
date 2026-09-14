---
name: write-task
description: >
  Turn a rough description into a task file a stranger could pick up: verb-first
  title, Why, What, Scope, Done when. Follows a bundled cheat sheet on ticket
  writing and plain language. Marks what it does not know as open questions
  instead of inventing context. Use when the user wants a task, ticket, story,
  bug report, spike or chore written up from a description, or /write-task.
argument-hint: "[description] [--out PATH]"
---

# Write a task

Produce one task as a Markdown file. The reader has none of your context and is skimming on a phone.

**Read `CHEAT-SHEET.md` next to this file before drafting.** It carries the section anatomy, the per-type shapes, the bad→good table and the final checklist. Everything below assumes you have read it.

## 1. Take the description

Use what the user gave you. If they named a file, issue or URL, read it. Do not start an interview — that is `grill-task`'s job.

## 2. Classify the type

The shape depends on it (cheat sheet §4):

| Type | Shape |
|---|---|
| Feature / story | Why → What → Scope → Done when → Links |
| Bug | Steps to reproduce → Expected → Actual → Environment → Impact → Evidence |
| Investigation / spike | Question (one sentence) → Time box → Deliverable |
| Chore / technical | Outcome (not activity) → In/out of scope → Dependencies → Exit criteria |

Unclear? Pick the closest, say which you picked, and move on.

## 3. Draft it

Follow the cheat sheet. The rules that get broken most often:

- **Why: three sentences, 15 words each, hard cap.** Count the words before you move on. This is the section people actually skip, and a fourth sentence guarantees it.
- **Title: verb first**, ~7 words, names the thing affected, makes sense in a list of 50 tickets a month from now. A bare noun is a topic, not a task.
- **One outcome.** If *What* needs an "and", you have two tasks — say so.
- **Done when** is ≤ 8 yes/no checks, covering happy path, failure path and one edge case.
- **No vague adjectives.** No *fast, simple, clean, better, robust, intuitive, seamless* without a number next to it.
- **Say what's out of scope**, especially the thing a reader would assume is in.
- Sentences under 25 words, paragraphs under 3 sentences, one idea per bullet.

## 4. Never invent the context

This is the rule that matters most here, because you will be given three lines and asked for a full task.

<hard-rule>

Every factual claim in the task — who is affected, how often, what it costs, what the constraint is, what the deadline is — must trace back to something the user actually said or something you verified in the repo, docs or tracker.

Anything else is marked in place, attached to the claim it qualifies:

> Mobile only. Open question: does this need to work offline?

> Sorted newest first. Assumption: the API already returns `created_at`.

**Inline, never a section of their own.** There is no "Open questions" heading in the anatomy table, and collecting gaps in a bucket at the bottom separates each one from the thing it undermines. A gap next to the claim gets answered; a gap in a list at the end gets skimmed past.

Never silently fill a gap with a plausible business justification. A visible gap gets answered; a hidden one gets built wrong.

</hard-rule>

If the *Why* itself is unknown, or you are carrying more than about three open questions, the task is not ready. Write it anyway, then tell the user plainly which parts are guesses and offer `grill-task` to close them.

### Which gaps are worth marking

Not inventing context does not mean interrogating every unknown. Apply one test before you mark anything:

**If this turns out to be wrong, does it change what someone builds or decides?** If not, leave it out.

Things that fail that test, and must not be marked:

- **The reader's own shorthand.** If they say "cleanliness", "tidy" or "sensible defaults", they know what they mean. Write it down and move on. Never ask someone to define their own word.
- **Anything they already know.** An exact date, a figure on a dashboard they look at daily. You are writing the task for them, not auditing them.
- **A detail that is off by a day, a rounding, or a name.** Precision that changes nothing is noise.
- **Anything you have already raised.** Once. If they didn't answer, they didn't think it mattered.

The *no vague adjectives* rule applies to **Done when**, where a check must be runnable. It does not apply to a constraint, a scope note or an aside where the reader knows their own meaning. Applying it there is pedantry and makes the task worse.

A task with no marked gaps is the normal case, not a failure.

## 5. Run the checklist

Check the draft against the cheat sheet's 60-second check (§6) and fix what fails. Read it once as the assignee, once as QA. Halve the word count, then look again for what else can go.

Two counts to do literally, not by eye:

- *Why* is at most 3 sentences, each at most 15 words. Over on either, cut until it isn't.
- No section runs longer than the table in §1 allows.

A task that survives this is shorter than feels right. That is the point — humans skim on a phone and do not read past the first line.

## 6. Write the file

Slug is the title, lowercased, kebab-cased, stop words dropped, ~5 words (`Add CSV export to the orders page` → `add-csv-export-orders`).

- Default path: `TASK-<slug>.md` in the current directory.
- `--out PATH` overrides it. A directory means `PATH/TASK-<slug>.md`.
- Never overwrite silently: if the file exists, show the user and ask.

Start the file with the title as an `# H1`.

**Write only *Why*, *What* and *Done when* unless another section earns its place.** That is the cheat sheet's minimum viable ticket; §1 says the rest is added *as needed*, not by default. Use only the section names in that table — never invent one.

A section earns its place when it answers a question the reader would otherwise have to ask. It does not earn its place because the type table mentions it, or because you have material that would fit. Dashboard figures, tables and evidence belong behind a link, not pasted in.

## 7. Hand back

Print the file's full contents inline in your reply, inside a fenced code block, then the path below it. Shell output from `cat` does not reliably reach the user's console, so a tool call is not a substitute.

Then say which parts are guesses, so they are visible without re-reading. In your reply, not as a section in the file.
