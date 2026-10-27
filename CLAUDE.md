# Casebook - AI mystery game

Working title: **Casebook**. A story-driven detective game where AI agents play the suspects, run the story and judge the player. Personal portfolio project aimed at AI engineer / GenAI roles on AWS: it must be fun to play AND show real multi-agent depth (memory, hidden state, planning, guardrails, evals, cost control).

Keep it fully separate from any employer systems: personal AWS account, personal machine, nothing reused from work projects.

---

## 1. The game in one paragraph

The player is a detective. Each case is a mystery (not only murder) told in acts with twists. The player questions AI suspects who have personalities, secrets and alibis, who lie consistently and crack under pressure. They search rooms, collect evidence, catch contradictions, and live through events that happen mid-case (a suspect vanishes, a second crime, evidence disappears). They spend insight points on actions, then accuse a culprit with motive, method and evidence. A judge agent scores the reasoning and tells the reveal. XP from cases raises the player's rank and unlocks abilities and harder cases.

## 2. Core rules (never break these)

1. **The hidden truth never reaches the player.** It lives server-side only. No API response contains it until the reveal.
2. **Each suspect agent sees only its own slice** of the truth (its secret, alibi, what it saw, what it lies about), never the full case.
3. **Player-facing writers see only player knowledge.** The journal, image, newspaper and recap agents read a separate `player_knowledge` record (clues found, statements heard, events witnessed), never the hidden truth.
4. **A continuity checker** reviews suspect answers and improvised events against the truth before the player sees them: no contradictions with the truth, no leaks.
5. **Points, XP and game state are changed by code, never by an LLM.** Agents can propose ("this is a valid contradiction"), deterministic code applies the change.
6. **Every case must be solvable and fair:** exactly one solution, and the clues available can prove it.
7. **All agent output that drives game logic is structured** (Pydantic schemas), validated, and retried on failure.

## 3. Cases

- **Mystery types:** theft, disappearance, fraud, sabotage, blackmail, forgery, murder. Vocabulary adapts (culprit/method instead of killer/weapon).
- **Themes:** country manor, train, film set, startup office, wedding, cricket club, etc.
- **Length:** 20–40 minutes per case. Long-term play comes from the career (section 7), later a season arc.
- **Story in acts:** 1) the crime, 2) the twist, 3) the escalation, 4) the solution.
- **Twist types:** obvious suspect is innocent but hiding something else; the victim had secrets; two crimes with two culprits; the "helper" is involved; it wasn't the crime it seemed (e.g. insurance fraud); hidden relationship between suspects.
- **Mid-case events:** suspect goes missing, second crime, evidence tampered/destroyed, new arrival (lawyer, relative, journalist, witness), true or false confession, threat to the detective, storm/blackout delays forensics.
- **Event triggers:** story beats (e.g. after N clues found), pacing (player stuck -> new lead), reaction (accusing too early -> culprit gets bolder; ignoring a suspect -> they act).
- **Planned vs improvised events:** planned events/twists are written into the hidden truth from the start (v1). Improvised events come later and must pass the continuity checker.

### Who writes cases
All cases use **one case file format**, whoever writes them.
1. Hand-written cases first (Markdown or YAML in the repo, `cases/`). These also become few-shot examples for the generator.
2. Hybrid: human writes a short outline, the case writer agent fills it in.
3. Fully generated: case writer + validator loop.
4. Later: an ingestion agent can read cases from other sources (e.g. a personal Confluence/Notion page) and convert them to the case format.

### Case file contents (sketch, refine during implementation)
- `meta`: id, title, mystery_type, theme, difficulty
- `public`: brief shown at start, setting, rooms, initial suspect public profiles
- `truth` (server-only): culprit(s), motive, method, real timeline of events
- `suspects[]`: name, role, personality, voice/style, alibi (claimed), what they actually did, what they saw, secret, what they lie about, when they crack (conditions), relationships
- `clues[]`: id, name, location, description, what it proves, requirements to find (room, key, event, act), optional image prompt
- `rooms[]`: id, name, locked?, unlock condition
- `acts[]`: id, goal, unlock condition, twist reveal
- `events[]`: id, act, trigger condition, effect (suspect location change, clue removed/added, new character, new room state)
- `solution`: required culprit, motive, method, key evidence ids, scoring rubric

## 4. Agents

### Story agents (behind the scenes)
| Agent | Job |
|---|---|
| Case writer | Generates a full case from type + theme + difficulty (+ optional outline) |
| Case validator | Checks solvability/fairness, one culprit, no plot holes; sends back for repair |
| Director | Watches progress and fires events/twists at the right moments; adjusts pacing and difficulty |
| Continuity checker | Checks suspect answers and events against the truth; blocks leaks and contradictions |

### Characters
| Agent | Job |
|---|---|
| Suspects | Answer in character, lie consistently, remember the conversation, slip under pressure, react to evidence |
| Suspect-to-suspect talk (later) | Suspects talk between player turns, make deals, frame others; player may overhear |
| Culprit behaviour (later) | Plants red herrings, destroys evidence, blames others when the player gets close |
| Partner ("Sergeant Rao") | Hints, challenges weak theories, remembers past cases (long-term memory) |
| New arrivals | Witnesses/lawyers/relatives introduced mid-case with consistent backstories |

### Detective tools
| Agent | Job |
|---|---|
| Notebook | Extracts statements, builds the timeline, flags contradictions |
| Forensics lab | Async analysis of evidence, results arrive later |
| Theory checker | Tells the player which parts of their theory the evidence supports |
| Judge | Scores the accusation (culprit, motive, method, evidence) and writes the reveal |
| Journal writer | Writes the detective's journal from player knowledge only; "previously on" recaps |
| Image prompts | Scene, event, evidence images and suspect portraits by mood (generated once, cached) |

### Production
| Feature | Job |
|---|---|
| AI play-testers | Automated detective agents play many cases; measure solve rate, leak rate, contradiction rate, points balance |
| Model routing | Cheap model for suspect small talk and routing; stronger model for case writer, director, judge |
| Tracing + cost | Trace every agent run; report cost per case |

## 5. Points and progression

Two currencies:
- **Insight points** - earned and spent inside a case.
- **XP** - earned at the end of a case, kept forever, raises rank.

Earning insight points (starting values, tune with play-testers):
| Action | Points |
|---|---|
| Find a clue | +10 |
| Catch a valid contradiction | +20 |
| Make a suspect reveal their secret | +30 |
| Correctly link a clue to a suspect | +15 |
| Handle a mid-case event well | +25 |

Spending:
| Action | Cost |
|---|---|
| Basic question | free (limited per suspect by rank) |
| Extra question | 5 |
| Confront with evidence | 10 |
| Search a room | 10 |
| Search a locked room with its key | free |
| Forensics test | 20 |
| Partner hint | 25 |
| Theory check | 30 |
| Bribe a witness / call in a favour | 40 |

XP at case end: correctness of culprit/motive/method, quality of evidence cited, unspent points, hints used.

Ranks:
| Rank | Unlocks |
|---|---|
| Constable | 3 free questions per suspect, basic cases |
| Sergeant | 4 free questions, forensics lab, two-twist cases |
| Inspector | 5 free questions, read body language, suspects who talk to each other |
| Chief Inspector | Search warrants, culprit who fights back |
| Legend | Season-final cases, create-your-own case |

Abilities: read body language (15), search warrant, stake-out, plant a rumour, second opinion.
Penalties: wrong accusation (big points + XP loss, culprit gets bolder), pushing too hard without evidence (suspect refuses to talk; costs points to recover), out of points → must accuse.

The judge validates claimed contradictions/links before points are awarded (no farming by guessing). The director uses the player's points balance to tune difficulty. Suspects may respond differently by rank.

## 6. API v1 (start here — API first, UI later)

| Endpoint | Purpose |
|---|---|
| `POST /games` | Start a game for a case → game id + public brief |
| `GET /games/{id}` | State: act, suspects (public), rooms, clues found, points, free questions left |
| `POST /games/{id}/suspects/{sid}/ask` | Ask a question → streamed answer, contradictions found, new events, points delta |
| `POST /games/{id}/suspects/{sid}/confront` | Show a clue or statement |
| `POST /games/{id}/rooms/{rid}/search` | Search a room → new clues, events, points delta |
| `GET /games/{id}/notebook` | Statements, timeline, contradictions |
| `GET /games/{id}/journal` | Journal by act |
| `GET /games/{id}/events` | Story events so far |
| `GET /games/{id}/gallery` | Images (later) |
| `POST /games/{id}/accuse` | Culprit, motive, method, evidence → score, XP, reveal |
| `GET /players/{id}` | XP, rank, unlocked abilities, case history |

Every action response may carry: new events, new journal entries, points ledger entries. Keep a points ledger (earned/spent with reasons).

Game state split:
- `truth` — server-only, from the case file
- `world_state` — current suspect locations, room states, clue availability, act
- `player_knowledge` — what the player has found/heard/witnessed
- `conversations` — per-suspect history
- `ledger` — points earned/spent

## 7. Progression and replay (later)
Detective career with ranks; daily case (one generated case per day for everyone, with a leaderboard — also keeps generation cost low); season arc with a mastermind across cases; create-your-own case; case history and replayable reveals.

## 8. Tech and cost

- **Agents:** LangChain + LangGraph, models on Amazon Bedrock (small model for suspects/routing, stronger model for case writer/director/judge).
- **API:** API Gateway + Lambda (or a small container) with streaming responses for suspect answers.
- **Data:** DynamoDB (games, player knowledge, conversations, ledger, players), S3 for cases and images. Use transactions for points updates. LangGraph checkpointer on DynamoDB for durable runs.
- **Images/voice (later):** Nova Canvas for portraits and scenes (generate once per case, cache in S3); Polly or Nova Sonic for suspect voices.
- **Guardrails:** structured outputs + continuity checker; Bedrock Guardrails for player chat input.
- **Observability:** tracing (LangSmith or self-hosted Langfuse, or CloudWatch/X-Ray) with cost per case.
- **Cost:** least-cost serverless, pay-per-use, nothing always-on. Put an API key or Cognito in front so nobody else can run up the Bedrock bill.
- **Local dev:** runs locally with a CLI client first (Python + Rich) before any web UI.

## 9. UI (after the API works)

Small web app (React + Vite + Tailwind) on S3 + CloudFront.
Look: polished **blue and white** — navy header (#13265c), light page (#f4f7fb), white cards with soft blue-grey borders (#dbe3ee), primary blue buttons (#1d4ed8), amber highlight for contradictions/conflicts. Serif display headings (Playfair Display), Inter body, typewriter font (Special Elite) for case notes.
Screens: case board (brief, suspect cards with mood + stress meter, rooms, partner hint, latest finds, points/questions counters), interrogation room (portrait, stress, what you know, chat with contradiction alerts, quick questions, show evidence, voice), evidence locker + timeline (clue cards, conflicting statements highlighted, accuse button). Later: map, evidence board, journal, newspaper, gallery.

## 10. Build order

1. **v1 (API + CLI):** one hand-written theft case ("The Vanishing Sapphire" style: 4 suspects, ~9 clues, one locked room), suspect agents with secrets and memory, room search, evidence locker, notebook with contradictions, one twist, two planned events (a suspect goes missing; a clue disappears/gets planted), insight points + ledger, text journal, accusation + judge + reveal.
2. Director driving planned events and pacing; partner hints.
3. Case writer + validator (hybrid outlines first, then fully generated).
4. AI play-testers + evals in CI (solve rate, leak rate, contradiction rate, points balance, cost per case).
5. XP, ranks, abilities; culprit behaviour; suspect-to-suspect talk; improvised events.
6. Web UI, images, voice, partner memory across cases, daily case.

Rule of thumb: get one agent deep and measured before adding the next.

## 11. Portfolio notes

- Present it as **"a multi-agent story system with hidden state, evaluated at scale"**, with the game as the environment.
- Deliverables: README with architecture diagram, eval numbers and cost per case; 90-second demo video (suspect cracks under evidence, a suspect goes missing mid-case, overheard conversation, culprit plants evidence, the reveal); LinkedIn posts as a build series.
