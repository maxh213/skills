# Writing Tasks People Can Actually Read

A cheat sheet for software engineering tickets, stories, bugs and chores.

**The one rule:** write for a reader who has none of your context and is skimming on a phone.

Two facts drive everything below:

- People scan; they don't read. Nielsen Norman Group found 79% of readers scan a new page and only 16% read word by word.
- The writer is the only person with the full picture in their head, and usually doesn't notice how much context they're carrying.

---

## 1. Anatomy of a task

Every section answers one question. If two sections answer the same question, merge them.

| Section | Question it answers | Length |
|---|---|---|
| **Title** | What needs to happen, at a glance? | ~7 words, verb first |
| **Why** (context) | What problem, for whom, and what if we don't? | 1–3 sentences |
| **What** (goal) | What will be true when this is done? | 1 sentence |
| **Scope & constraints** | What's in, what's out, what can't change? | Bullets |
| **Done when** (acceptance criteria) | How do we check it works? | ≤ 8 testable bullets |
| **Links** | Where are the designs, docs, related tickets? | Links only |
| **Proposed approach** (optional) | Any starting idea for *how*? Clearly a suggestion. | Bullets |

Minimum viable ticket: Why, What, Done when. The rest is added as needed.

### Title

- **Always actionable.** Start with a verb that says what changes: *Add*, *Allow*, *Fix*, *Remove*, *Stop*, *Show*. A bare noun (*"CSV export"*, *"Login page"*) is a topic, not a task.
- Verb first, then the specific thing. *"Fix login failing on Firefox after password reset"*, not *"Issue with the login page some users reported"*.
- Name the user, system or process affected.
- Say what changes for the user, not the internal activity. *"Add CSV export to the orders page"*, not *"CSV work"* or *"Refactor export module"*.
- Bugs too: *"Fix checkout total showing £0.00 with a discount code"*, not *"Checkout total wrong"*. The verb tells the reader it's theirs to act on; the detail after it tells them where to look.
- It should make sense in a list of 50 other tickets, a month from now.

### Why

- State the problem in plain terms: who is affected, how often, what it costs.
- Say what happens if we don't do it. This is what lets someone else prioritise.
- Part of something bigger? Link the epic. Don't repeat it.

### What

- Finish the sentence *"This is done when…"* or *"Users can…"*.
- One outcome. If the sentence needs "and", you probably have two tasks.
- Describe the result, not the implementation.

### Scope & constraints

- One requirement per bullet.
- Say what's out of scope, especially the thing a reader would assume is included.
- List hard constraints: *"must use the existing auth service"*, *"mobile only"*.
- Include what must **not** happen. Negative cases become test cases.
- Don't dictate the solution unless it's a real constraint. The implementer owns the *how*.

### Done when (acceptance criteria)

- Each criterion is a yes/no check someone could actually run.
- Replace "fast", "user-friendly", "robust" with something measurable: *"loads in under 2 seconds for accounts with up to 10k orders"*.
- Cover the happy path, the failure path and at least one edge case.
- More than ~8 criteria means the task is too big. Split it.
- Convey intent, not a final design. Too narrow leaves no room to build; too broad can't be tested.
- Given/When/Then helps when behaviour depends on state:
  - Given a logged-out user, when they open /orders, then they see the login page.

### Links & attachments

- Link the design, doc, parent ticket, incident. Don't paste them in.
- One source of truth per fact. Contradicting docs are worse than none.
- Screenshots and short logs in a code block beat prose descriptions of them.
- Descriptive link text: *"Figma: checkout flow v3"*, not *"here"*.

---

## 2. Make it readable

### Structure

- **Most important thing first.** In the ticket, in each section, in each sentence. Assume the reader stops after the first line.
- **One idea per paragraph.** Three sentences maximum. Longer than that, it's a list.
- **Bullets for things, numbers for sequences.** Only number steps the reader follows in order.
- **One sentence per bullet.** Two sentences in a bullet means two bullets.
- **Label sections so they can be skimmed.** *Why*, *Done when*, *Out of scope* beat *Background* or *Notes*.
- **Skip the introduction.** No *"This ticket is about…"*. Start with the problem.
- **Halve the word count.** Then look for what else can go.
- **White space is a feature.** Blank lines between sections. No walls of text.
- **Bold sparingly.** A keyword or two per section, never whole sentences.

### Sentences

- Under 25 words. Under 15 is easier still.
- Active voice: *"The form saves on blur"*, not *"The form is saved when blur occurs"*.
- Keep subject and verb close together.
- Be concrete: exact values, field names, error codes, URLs. *"Returns 403"*, not *"errors out"*.
- Cut filler: *in order to* → *to*; *at this point in time* → *now*; *the fact that* → delete.

### Words (jargon and shorthand)

- Everyday words: *use / start / end / show*, not *utilise / initiate / terminate / surface*.
- Spell out every acronym on first use: *Know Your Customer (KYC)*. Even the ones "everyone knows".
- Define or link any term a new hire wouldn't know: codenames, internal service names, team slang.
- One name per thing. Don't call it the *orders page*, *order history* and *OH* in the same ticket.
- No vague adjectives: *fast, simple, clean, better, robust, intuitive, seamless*. Say what you'd measure instead.
- No superlatives or sales language.
- Write what should happen, not *"fix"* or *"improve"*. *"Fix login"* tells nobody when to stop.

### Be honest about gaps

- Settle unknowns that change the work before you write, by asking the person who knows.
- Leave out the ones that don't. The reader has the organisation's context and does not need "who controls DNS?" spelled out.
- A question written into the ticket is neither: it gets built late while someone chases it. Ask or drop, never mark.

---

## 3. Size

- One task = one outcome, one person, a few days. Longer than that, split.
- A Done list with a dozen items, or several unrelated scenarios, is an epic in disguise.
- Split by scenario (normal user / admin), by layer (UI / API / integration) or by step (first 5 orders / pagination). Each piece keeps its own Why, What and Done.
- Big unknowns? Write a time-boxed investigation task first, then the real tasks.

**INVEST quick check:** Independent, Negotiable, Valuable, Estimable, Small, Testable.
If you can't estimate it, the goal is unclear. If you can't test it, the Done is unclear.

---

## 4. By task type

### Feature / story

Why → What → Scope → Done when → Links.
The *"As a [who], I want [what], so that [why]"* format is optional. Use it if it helps; drop it if it reads like filler.

### Bug

A bug report is a story: what you did, what you expected, what happened instead.

- **Title:** verb + what failed + where. *"Fix checkout total showing £0.00 when a discount code is applied"*.
- **Steps to reproduce:** numbered, starting from a known state (*logged in as X, on page Y*). Test your own steps as a stranger would.
- **Expected** and **Actual:** two labelled lines.
- **Environment:** app version, browser/OS, account type, data conditions.
- **Evidence:** screenshot, short log in a code block, video link.
- **Impact:** how many users, blocked or just annoyed, workaround or none. This sets priority.
- Facts, not opinions. *"Button does nothing on click"*, not *"button is broken and awful"*.

### Investigation / spike

- The question to answer, in one sentence.
- The time box.
- The deliverable: a decision, a short doc, or a list of follow-up tasks.

### Chore / technical task

- The outcome (*"staging runs Node 22 with no test regressions"*), not the activity (*"upgrade Node"*).
- In scope / out of scope.
- Dependencies that gate it.
- Exit criteria.

---

## 5. Bad → good

| Bad | Why it fails | Better |
|---|---|---|
| Fix login bug | No what, where or when | Fix 403 on login in Firefox 115 after password reset |
| Make the report faster | Not measurable | Speed up orders report to under 2s for accounts with ≤10k orders |
| CSV export | A topic, not an action | Add CSV export to the orders page |
| Update the docs so they're not out of date | No scope, no done | Update API auth docs to cover token refresh (added in v2.3) |
| Connect service A to queue B | Implementation with no outcome | Outcome first; *"connect A to B"* goes under Proposed approach |
| Build a purchases report | No why, no contents, no done | Why + bulleted requirements + *"customer finds their last 5 orders in ≤2 clicks"* |
| Leverage the new KYC flow to surface HEIC in admin | Jargon, undefined acronyms, no why | Let support agents upload HEIC (iPhone) photos of ID documents in the admin tool |

---

## 6. Before you save: the 60-second check

- [ ] Could a new team member pick this up tomorrow without asking me anything?
- [ ] Does the title start with a verb and say what changes?
- [ ] Does the title make sense in a list of 50 other tickets?
- [ ] Can I say exactly when it's done?
- [ ] Is the *why* there, and does it say what happens if we don't?
- [ ] Every acronym spelled out, every internal term defined or linked?
- [ ] Any paragraph over 3 sentences? Any sentence over 25 words?
- [ ] Any *fast / easy / better / robust* without a number?
- [ ] Anything a reader would assume is included that's actually out of scope? Said so?
- [ ] Does it read fine on a phone?
- [ ] Read it once as the assignee, once as QA.

A few extra minutes here saves hours of clarification later.

---

## 7. Templates

### Feature

```markdown
**Why**
[1–3 sentences: problem, who's affected, cost of not doing it]

**What**
[One sentence: what will be true when this is done]

**Scope**
- In: …
- Out: …
- Constraints: …

**Done when**
- [ ] …
- [ ] …

**Links**
- Design: …
- Related: …
```

### Bug

```markdown
**Steps to reproduce**
1. Logged in as …, go to …
2. …

**Expected**
…

**Actual**
…

**Environment**
Version …, browser/OS …, account type …

**Impact**
[users affected, blocked?, workaround?]

**Evidence**
[screenshot / log / video]
```

---

## Sources

Readability and plain language

- Nielsen Norman Group, *How Users Read on the Web* — scanning behaviour, inverted pyramid, one idea per paragraph, halve the word count. https://www.nngroup.com/articles/how-users-read-on-the-web/
- Nielsen Norman Group, *Concise, Scannable, and Objective* — technical and non-technical readers both want scannable text. https://www.nngroup.com/articles/concise-scannable-and-objective-how-to-write-for-the-web/
- US National Archives, *Top 10 Principles for Plain Language* — major point first, active voice, everyday words, explain terms on first use. https://www.archives.gov/open/plain-writing/10-principles.html
- Digital.gov, *Plain language guide* — write for your actual audience; plain isn't dumbed down. https://digital.gov/guides/plain-language
- GOV.UK, *Writing for GOV.UK* — front-loading titles and headings, no introductions, vocabulary of the audience. https://www.gov.uk/guidance/content-design/writing-for-gov-uk
- ONS Service Manual, *Plain language* — active voice, spelling out acronyms, front-loaded headings. https://service-manual.ons.gov.uk/content/writing-for-users/plain-language

Ticket and task structure

- Chrissy Fleming, *A Guide to Writing Good Tickets* — Purpose / Requirements / Acceptance Criteria; requirements in bullets; "proposed implementation" as a labelled suggestion. https://www.chrissyfleming.com/post/a-guide-to-writing-good-tickets
- Matthew Goldman (ProductFTW), *Tips for Terrific Tickets* — ~7-word titles, the five Ws, impact and priority on every ticket. https://www.productftw.com/productftw-21-tips-for-terrific-tickets/
- Maxim Gorin, *Writing Engineering Tasks as a Team Process* — Context / Goal / Scope / Definition of Done, epics in disguise, task clarity checklist. https://maxim-gorin.medium.com/writing-engineering-tasks-as-a-team-process-afccc9767eb4
- Natasha Jaffe, *Writing good (aka closable) tickets* — the writer forgets the reader lacks their context; per-type minimum criteria. https://natashajaffe.substack.com/p/writing-good-aka-closeable-tickets
- Vaishnavi Sambrekar, *Writing Effective Engineering Tickets* — single source of truth, small sub-tasks, edge cases up front. https://vaishnavi-sambrekar.gitbook.io/product/writing-effective-engineering-tickets
- Heady, *Foundations of Agile Ticket Writing* — INVEST applied to tickets; keep acceptance criteria under 8. https://www.heady.io/blog/foundations-of-agile-ticket-writing-a-4-part-series
- Jira Templates, *Task template* — tasks need outcome, in/out of scope, dependencies and exit criteria. https://www.jira-templates.com/issues/task-template
- Zenhub, *GitHub Issues: Good to Great* — who / what / why in the issue itself. https://www.zenhub.com/blog-posts/best-practices-for-github-issues

Stories and acceptance criteria

- Agile Alliance, *INVEST* — origin and definition. https://agilealliance.org/glossary/invest/
- Kaizenko, *The 6 Attributes of Effective User Stories* — measurable criteria instead of "easy", "fast", "bug-free". https://www.kaizenko.com/6-attributes-of-effective-user-stories-invest/
- AltexSoft, *Acceptance Criteria* — not too narrow, not too broad; intent over solution. https://www.altexsoft.com/blog/acceptance-criteria-purposes-formats-and-best-practices/
- ProductPlan, *Acceptance Criteria* — Given/When/Then format. https://www.productplan.com/glossary/acceptance-criteria

Bug reports

- Apache Infrastructure, *Writing a good bug report* — useful vs useless titles; wanted / did / expected / happened. https://infra.apache.org/bug-writing-guide.html
- OpenSC wiki, *How to write a good bug report* — numbered steps, test your own instructions, version numbers. https://github.com/OpenSC/OpenSC/wiki/How-to-write-a-good-bug-report
- Simon Tatham, *How to Report Bugs Effectively* — the goal is to let the developer see the failure. https://www.chiark.greenend.org.uk/~sgtatham/bugs.html
- QA Wolf, *What Makes a Great Bug Report* — complete but concise; start reproduction from a known state. https://www.qawolf.com/blog/what-makes-a-great-bug-report
- Noah Sussman, *How to write a bug report* — a bug report as a three-part story. https://infiniteundo.com/post/36678096413/how-to-write-a-bug-report
