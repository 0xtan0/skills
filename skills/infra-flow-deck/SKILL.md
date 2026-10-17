---
name: infra-flow-deck
description: Build a short client presentation (HTML Artifact) that explains a cloud/on-chain system with an animated "Play" block diagram (trigger → compute → config/secrets → signing → queue → chain) plus a second Play diagram of the network path (VPC, subnets, security groups with ports, NAT, internet gateway, CDN origin, endpoints, bastion), a Play slide of the main IAM roles and critical policies, a release-path Play (branches → accounts, app image deploys), a data-protection matrix, plus a static accounts/regions/repos diagram, using AWS iconography and ~80% ASD-STE100 text. Starts with a research pass over the infra code (Terraform, task definitions, contracts) so every block and arrow is backed by code. Use when asked for a system/infra presentation, a "how it works" deck, an architecture diagram with a play button, a network or VPC diagram, an IAM roles overview, a release or deploy pipeline diagram, a data-protection or encryption matrix, or an accounts-and-repos ownership chart.
---

# Infra flow deck

Output: one private HTML Artifact, about 8 slides, for a meeting where the presenter talks.
The diagrams carry the meaning. The text is minimal. Every block, arrow and claim comes
from the code; nothing comes from memory or from docs alone.

Order of work: Step 0 set up → Step 1 research and write the ledgers → Step 2 build →
Step 3 check until `0 problem(s)` → Step 4 publish and report.

## Step 0 — Set up

1. Copy `assets/template.html` to one scratch path. Every revision and every publish uses
   that same path, so the Artifact URL stays the same.
2. Put the ledgers (Step 1) in a `ledger.txt` beside it. `assets/ledger.example.txt` shows
   the format; the ids and paths in it are invented.
3. Load the `artifact-diagramming` skill before you lay out an SVG. Follow the Artifact page
   contract (theme tokens, no doctype, side gutter).

The template is a working deck with a worked example: slide engine, Play/Step/Reset logic,
AWS-style tiles, account and region boxes, a dotted secondary flow and a brand-logo tile.
Change the data and the coordinates; do not rewrite the engine.

Engine facts:
- `player(svgId, prefix, steps, idleCaption)` runs one Play slide. Prefix `''` uses
  `#play/#back/#next/#reset/#cap`; `'n'` uses `#nplay/…/#ncap` (network), `'i'` uses
  `#iplay/…/#icap` (IAM), `'r'` uses `#rplay/…/#rcap` (release). Push its return value to
  `stops`. A step is `{n:[node ids], a:[arrow ids], c:'caption'}`; `a` may be empty.
  `player()` registers itself in `window.__players`; `scripts/check.py` reads that, so keep
  the line.
- `tile(id,cx,cy,color,glyph,label,sub,side)`: `side` is falsy (label below), `'l'`, `'t'` or
  truthy (right). A label below blocks any vertical line through that column. Move it aside.
- `chipRow(cy, items, x0)` draws grant chips beside a role tile. Each item is
  `[text, stripe colour, id, deny?]`; each chip is a `.node`, so a Play step can light it,
  and `deny?` adds the red outline. A chip is 360px wide; the check fails on text that runs past it.
- Arrow markers live in one hidden-but-rendered svg at the top of `body`. Never add `defs()`
  inside a slide: a marker in a `display:none` slide does not paint on other slides.
- Line classes: `.arr` solid main-flow arrow (every one must be in a Play step); `.arr deny`
  red dashed, for an explicit Deny or a permissions boundary; `.mon` dotted secondary flow;
  `.deploy` repo → account; `.uses` cross-account use. Paths use absolute `M H V L` only.
- Glyphs in `G`: core `clock`, `ecs`, `lambda`, `ssm`, `kms`, `sqs`, `rpc`, `hash`, `cube`,
  `target`; network `alb`, `nat`, `igw`, `ep`, `ec2`, `db`, `waf`, `r53`, `logs`, `user`;
  identity `role`, `gcp`; release `branch`, `cloud`; AI `brain`; brands `github`, `vercel`,
  `discord`, `pagerduty`, `slack`. Brand glyphs are white: give the tile the brand colour
  (`github` #24292f, `vercel` #000000, `discord` #5865F2, `pagerduty` #06AC38; `slack` is in
  colour, tile #ffffff). Add a brand only as its real logo path.
- The network, IAM, release and matrix slides are in the template as commented sections.
  Uncomment the section, fill `#net`, `#iam`, `#rel` or the `.mx` table, and register each
  Play with `player()`.

## Step 1 — Research the system in the code (mandatory, before drawing)

Research on the **deploying branch**: the branch whose merge applies to production. Compare
with the default branch only to note drift; draw what production runs. Delegate to one
subagent if the repo is large. Ask it for a factual brief with file paths.

1. Read the repo's `AGENTS.md` / `README` files, then the IaC (Terraform, CDK, etc.), the
   service code, the contracts and the deploy docs. Follow references to sibling repos.
2. **Decide what the chart must show.** Start from the main flow the user asks about. List
   the elements it touches, end to end, and keep only what the audience needs to understand
   that flow. Typical kinds of element:
   - Runtime components: tasks, functions, services, workers, monitors, jobs.
   - Triggers: schedulers, queues, events, webhooks, users.
   - Data and config: parameter stores, secrets, databases, queues.
   - Trust and signing: key stores, signers, roles that cross a boundary.
   - External parties: RPC/API providers, chat/alerting tools, chains, third-party services.
   - Boundaries: accounts, regions, networks, on-chain vs off-chain.
   Say which elements you leave out, and why.
3. **For each element you keep, find in the code what matters for the chart.** Only the
   facts that become a block, an arrow or a caption: what starts it; what it reads; what it
   writes or sends; who signs or authorizes for it, and with what; who pays for it (fees,
   gas, cost owner; look for exceptions); which boundary it sits in.
4. **Ownership.** Make a table of accounts × regions, and of repos → what each one deploys
   where, **only if** the system has more than one account or more than one region. If it
   does not, skip this table and the ownership slide.
5. **Network.** Read the network IaC in full: VPC and subnets (CIDRs, AZ count, which tier
   each resource sits in), route tables, NAT and internet gateways, private endpoints (and
   whether private DNS is on), every security group and every rule (source, port, CIDR or SG
   reference), load balancers (internal or internet-facing, listener default action), CDN
   origin type, service discovery, bastion or other human access, flow logs. Note what sits in
   the public subnets. Note which cloud API calls leave through NAT because no endpoint exists.
   Write the result as an **edge ledger** before you draw: one line per security group rule
   pair and per load balancer target group, as `source → destination :port (file:line)`.
   Grep for every rule resource (for AWS: `aws_vpc_security_group_ingress_rule`,
   `aws_vpc_security_group_egress_rule`, `ingress`/`egress` blocks, `aws_lb_target_group`,
   `aws_lb_listener`, `aws_vpc_endpoint`) across the root and every module it calls. Do not
   build the ledger from a summary or from memory.
6. **IAM.** Grep every role, policy, policy attachment, policy document, trust policy and
   permissions boundary in the root and its modules. Write an **IAM ledger**, one line per
   role: `role | trusted by + every condition | main grants | explicit denies, boundary |
   file:line`. Conditions are facts the audience needs: OIDC repo id, ref, environment,
   ExternalId, SourceAccount, session name. Then pick:
   - **Main roles:** roles that cross a boundary (another account, CI, a customer), can change
     infrastructure, or touch customer data. Roles that only write their own logs are left out
     (report them).
   - **Critical policies (0–5):** explicit Deny statements, permissions boundaries, `*`
     resources, `iam:PassRole`, cross-account `sts:AssumeRole`. Quote the sid. If none exist,
     say so; do not invent one.
7. **Release path.** Read every CI workflow: trigger (`pull_request` or `push`, branches,
   `paths`), the CI environment, the role it assumes, fork-PR guards, build steps before
   apply, and manual dispatch. Read the repo rules for who merges releases. For app images,
   read the deployer roles (trust ref, what they can push and update) and whether the IaC
   ignores task-definition changes. App-repo workflows outside this repo are UNCONFIRMED
   unless you read them.
8. **Data stores.** List every store that holds customer, audit or secret data: databases,
   buckets, the IaC state, log groups, secret stores. For each: encryption key (customer
   KMS, cloud-managed, storage-managed) and TLS, retention (backups, Object Lock, versioning,
   lifecycle, log days, deletion protection, secret recovery window), availability (Multi-AZ,
   copies in another region or account), exposure, who can read the data (not the config)
   including CI after its denies, and audit (data events, database logs). Grade each cell
   strong, partial or gap, with a file:line.
9. **Live state.** For every compute element, read its desired count (or replicas, or
   schedule) and the gate in front of it (WAF default action, listener rule, feature flag).
   A service at zero, or blocked at the edge, is parked; the deck says so.
10. **Public exposure.** Grep `public_access_block`, `principals` with `"*"`, `acl`,
    `publicly_accessible`, `associate_public_ip_address`, `internal = false`, open security
    group CIDRs. List every public object, endpoint or account-wide relaxation, and what it
    costs (for example, a bucket that loses one layer of protection).
11. **Made by hand.** Grep for data lookups of trust anchors (DNS zones, OIDC providers,
    state buckets, connections, account settings) and for "console", "by hand", "out of
    band", "manual apply" in comments and deploy guides. Keep one list: "made by hand,
    outside the IaC".
12. Mark everything you cannot confirm in the code as UNCONFIRMED. Tell the user about it.
    Do not draw it as a fact.
13. Get the **order of steps from the code**, not from the user's list. If the code order
    differs, use it and say so.

Then write `ledger.txt` for the check from the edge and IAM ledgers:
`arrowId | source -> destination :port | file:line`, or `- | left out: reason | file:line`.

## Step 2 — Build the deck

Slides:
1. Title.
2. **Main flow diagram with Play.** Blocks from the first trigger to the final effect. Play,
   Step back, Step next and Reset buttons, plus one caption per step.
3. **Network flow diagram with Play.** One VPC, drawn once (not once per AZ; write the AZ
   count and the subnet CIDRs in the box titles). Bands: public subnets, private subnets.
   Outside the VPC: the CDN or client, the operator, the internet. Play steps, in this order:
   traffic in (CDN origin, load balancer SG, task SGs), app to data (database SGs, internal
   load balancers), traffic out (task egress, route to NAT, internet gateway), isolated paths
   (functions with no internet route, endpoints), human access (bastion, port forwards).
   Put the port beside every arrow as a `.tag` text (`:443`, `:5432`). Flow logs and other
   observers are dotted and not in the Play.
   Skip this slide if the system has no network of its own (for example, only managed
   serverless services), and say so in the report.
4. **Main IAM roles with Play.** Three columns: who can assume (repo and branch, cloud
   service, another account) → role tile (Security #DD344C) → what it reaches (resource tiles
   or chips). Put the trust conditions as `.tag` text on the trust arrow (`ref: main`,
   `ExternalId`). Draw each critical policy as a red `.arr deny` line to what it blocks, with
   the sid or the action as a tag (`Deny ssm:*`). One Play step per role group (CI,
   deployers, runtime, cross-account), then one step per critical policy. Use the same names
   as the other slides.
5. **How a change reaches prod, with Play.** Branch tiles on the top row (labels above),
   one account tile under each branch it applies, app repos and deployer roles on a bottom
   lane. Arrow tags say the gate (`PR + plan`, `merge: apply`, `push to main`). Steps follow
   the real order; say which steps a person does by hand.
6. **Where the data lives (matrix).** An HTML table (`.mx`), not an SVG. One row per store,
   columns: encryption, retention, availability, exposure, who can read the data, audit.
   Each cell starts with a status icon and label (✓ strong, ◐ partial, ✕ gap) and uses the
   status tokens `--good/--warn/--crit`, never series colours. Each cell has a `title` with
   its source. A footer states cross-cutting gaps (no copy in another region, CI that can
   edit its own denies). The matrix keeps its own font sizes; it must fit the slide without
   scrolling.
7. **Accounts, regions and repos.** A static diagram. Only if Step 1, Ownership, applies.
8. **Key points**, 3–5 short lines. Use only claims you verified in Step 1. Include one
   network claim if it is true (for example, what is in the public subnets). The "made by
   hand" list goes here or on the accounts slide.

## Rules (learned from review; follow all of them)

**Accuracy**
- Draw every signing relation the code has. When a key store (for example KMS) does the
  signing, every component that uses it gets its own arrow to it. Look for more than one signer.
- Do not write an absolute claim ("X never pays", "Y holds no secrets", "Z always…") until
  you search the code for exceptions. If an exception exists, say it or drop the claim.
- Every safety or reliability property on a slide must come from the code or the config.
  Do not add plausible-sounding guarantees (quorums, retries, redundancy) that you did not find.
- Draw every trigger and every read/write for each element you keep. Do not draw only the
  ones on the main path.

**Scope and noise**
- Do not copy the same diagram once per environment (dev/staging/prod side by side). Show
  one environment, by default the production one, and say so.
- If production is multi-region, show it. Put region boxes inside each account, and label
  each region with its role (primary, replica, standby, backup).
- **Main flow vs secondary flows.** The Play steps cover only the main flow the user asked
  about. Draw other flows that share the same infrastructure (monitoring, alerting, admin or
  batch jobs) as dotted lines. Keep them out of the Play steps, and give them a short legend.

**Coverage (check before every publish)**
- On a slide that spans environments (release path, accounts), read every root, not only
  production's. A deploy path created by a module that every root calls (a deployer role, a
  pipeline, a trust) reaches every environment: draw one arrow per environment, with the
  branch or condition each one trusts. "Prod only" needs proof that the other roots do not
  call it.
- A load balancer, proxy, gateway, endpoint or queue is never the end of an arrow. Draw it
  and the component behind it, with the second hop as its own arrow and step. Do not merge
  "internal ALB" and the service behind it into one tile.
- Walk the edge ledger line by line. Each line is an arrow on the slide, or it is in the
  short "left out" list you report, with the reason. Nothing is left out silently.
- Walk every tile: each database has its owner, each load balancer has its targets, each
  endpoint has its callers, each function has what it reaches. One owner per database: if
  there are three databases, show three or report which are left out.
- If one tile stands for several resources (two NAT gateways, two bootstrap functions), write
  "× N" on the tile and draw an arrow to every target the group reaches.

**Live state, exposure and ownership**
- A parked service (Step 1, Live state) is drawn grey with "parked: 0 tasks" or "blocked at
  edge", and its captions say so.
- Every public object or relaxation (Step 1, Public exposure) is drawn or stated on a slide,
  with what it costs.
- **Every account box and repo arrow has a source.** Back each account box and each
  "repo → account" arrow with a root in the IaC (for example `environments/<name>`) or a
  deploy workflow on the deploying branch. Grep the account id. An account with no code is
  dropped or labelled ("being removed, no IaC"); never say "every account" without counting.
- The "made by hand, outside the IaC" list is on a slide, as one list.

**Matrix accuracy**
- Grade "who can read" on data, not config. A CI role that is denied object reads but can
  read the state file, or every log group, is partial or gap there.
- A cloud default not set in the code (default key, default rotation) is stated as "AWS key"
  or "not in code", never as a customer KMS key.
- "Not in code" is partial, not strong: something made by hand cannot be checked from here.

**Network accuracy**
- Say what each layer does. A security group drops traffic; a listener default returns 403.
  Do not give one the other's behaviour.
- "No public IP" needs proof for each resource: internal load balancer, `assign_public_ip`
  false, `publicly_accessible` false, no public IP on the instance.
- Name SG rules by what they reference ("admits only the edge ALB"). If a rule uses a CIDR
  (for example egress 443 to 0.0.0.0/0), say so. Do not call it "locked down".
- If a gateway is per AZ, say "× 2, one per AZ" on the tile. Do not draw it twice.

**Naming and icons**
- Use the same name for a thing on every slide. Take names from the code or the infra
  (account names, service names), not invented labels.
- Use official cloud service names and category colours (AWS: Compute #ED7100, Security
  #DD344C, App integration/Management #E7157B, Networking #8C4FFF, region boxes #00A4A6 dashed).
- For non-cloud services, use the real brand logo. Do not use a generic glyph.
- Name each component by its role, with its technology as the subtitle.

**Layout**
- No line goes through a tile or a label. Give each arrow its own corridor (its own x for
  vertical runs, its own y for horizontal runs). Allow at most one crossing, and only on a
  dotted secondary line.
- A trigger that starts more than one component sits between them. Its arrows fork.
- SVG text is at least 16px. Side labels must not touch the arrows.
- Port tags and boundary labels must not sit on a box border or another label. Put a tag in
  the gap between the arrow's start and the first border it crosses.

**Writing (~80% ASD-STE100)**
- Short sentences (max ~15 words), active voice, present tense, one instruction or fact per
  sentence.
- Use consistent terms. The captions say what moves, not how the code works.

## Step 3 — Check (before every publish)

Run the check (headless Chrome, no window opens):
`python3 <skill dir>/scripts/check.py <deck.html> --ledger <ledger.txt> --out <scratch dir>`.
It fails on labels that overlap labels, tiles, lines or box borders; lines through tiles;
SVG text under 16px; markers inside slides; path commands it cannot measure; Play steps with
missing ids; solid arrows no step uses; chip text past its chip; white glyphs on white tiles;
a matrix that scrolls; and ledger lines with no drawn arrow. Fix every FAIL and run it again
until it prints `0 problem(s)`. Then look at its screenshots (every slide, light and dark)
once. The check does not read meaning: the coverage walk in the rules is still yours.

## Step 4 — Publish and report

Publish as an Artifact from the same file path as before, so the URL stays the same.
Report what changed, what is UNCONFIRMED, what you left out (the `-` ledger lines and the
roles you dropped), the check result, and what you did not check visually.
Remind the user that the link is private until they share it.
