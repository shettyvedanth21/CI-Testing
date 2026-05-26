# Shivex Agentic Automation Blueprint

## Purpose

This document defines the **right user-facing meaning of agents in Shivex**.

The earlier direction of:

- Operations Agent
- Analytics Agent
- Reporting Agent
- Waste Analysis Agent
- Rules Agent

is **not the best product model**.

Why:

- those are mostly existing module names
- they feel like navigation or feature shortcuts
- they do not feel intelligent
- they do not feel autonomous
- they do not feel outcome-driven

That is why the earlier prototype felt weak.

## Correct Product Principle

In Shivex:

**Agents should not be page names.**

Agents should be:

- **goal-based**
- **automation-driven**
- **multi-step**
- **orchestrators of existing platform capabilities**
- **outcome-oriented from the user point of view**

A user should not feel:

- “this is Analytics renamed as Agent”
- “this is Reports renamed as Agent”
- “this is Rules renamed as Agent”

Instead, the user should feel:

- “I told Shivex what outcome I want”
- “Shivex built a plan”
- “Shivex configured the right actions”
- “Shivex is monitoring progress for me”
- “Shivex will tell me when something needs action”

---

## The Right Mental Model

### Bad model

```text
Agent = feature page
```

Examples:

- Analytics Agent = open analytics
- Reporting Agent = open reports
- Rules Agent = open rules

This is only relabeling.

### Good model

```text
Agent = goal + plan + actions + monitoring + result
```

Examples:

- Reduce energy cost
- Stop idle running waste
- Maximize uptime
- Reduce overconsumption
- Prepare daily operations briefing
- Onboard and verify device

This is real agentic behavior.

---

## What The Sample Prototype Got Right

The sample HTML points in the correct direction because it starts with:

- `What do you want to achieve?`

and then offers goals like:

- `Reduce Energy Cost`
- `Stop Idle Running Waste`
- `Maximize Machine Uptime`
- `Reduce Overconsumption`

That is much better because the user is not choosing a tool.
The user is choosing an **outcome**.

Then the agent can:

- build a plan
- configure rules
- schedule reports
- activate monitoring
- watch machines
- notify users
- present progress and results

That is the correct Shivex agent direction.

---

## Shivex Agent Model

The best customer-facing agents for Shivex should be these.

### 1. Reduce Energy Cost Agent

**User goal**

- lower energy cost across machine / plant / fleet

**What the agent can do**

- identify major cost drivers
- run waste analysis in the background
- schedule recurring cost reports
- configure alerting for abnormal usage
- recommend top devices to review

**Uses underneath**

- waste analysis
- reporting
- rules
- machine consumption data
- tariff-aware calculations

**User-facing promise**

- “I will help you reduce avoidable energy cost and track progress.”

---

### 2. Stop Idle Running Waste Agent

**User goal**

- detect and reduce idle running waste automatically

**What the agent can do**

- detect devices idling during active shift
- configure idle thresholds and alert rules
- notify plant users when waste exceeds threshold
- summarize daily/weekly idle-loss trends

**Uses underneath**

- machine live state
- idle detection
- rules
- notifications
- reporting

**User-facing promise**

- “I will watch for idle-running waste and notify the team before it grows.”

---

### 3. Maximize Uptime Agent

**User goal**

- increase uptime and reduce avoidable stoppages

**What the agent can do**

- track current shift uptime
- spot machines at risk
- trigger deeper analytics when needed
- recommend follow-up inspection or rule creation
- create periodic uptime review summaries

**Uses underneath**

- machine runtime state
- health score
- uptime calculations
- analytics
- alerts
- activity history

**User-facing promise**

- “I will help keep uptime high and surface machines that need attention.”

---

### 4. Reduce Overconsumption Agent

**User goal**

- catch excessive current / load / usage patterns early

**What the agent can do**

- monitor overconsumption conditions
- configure or recommend threshold rules
- identify repeat offenders
- connect abnormal usage to machine history

**Uses underneath**

- telemetry
- rules
- machine detail
- loss stats
- alerts

**User-facing promise**

- “I will watch for overconsumption and guide response before it becomes expensive.”

---

### 5. Daily Operations Briefing Agent

**User goal**

- receive a clean summary without opening five different pages

**What the agent can do**

- prepare a daily briefing
- summarize machine health, downtime, alerts, top losses, and recent changes
- schedule delivery by time and audience

**Uses underneath**

- reporting
- dashboard summary
- rule alerts
- waste summary
- fleet state

**User-facing promise**

- “I will prepare the daily operational briefing for your team.”

---

### 6. Onboard And Verify Device Agent

**User goal**

- onboard a machine correctly and confirm it is live

**What the agent can do**

- guide device creation
- map plant
- guide provisioning and hardware setup
- verify telemetry flow
- confirm the machine is operationally visible

**Uses underneath**

- onboarding
- plant mapping
- hardware inventory
- provisioning
- telemetry verification

**User-facing promise**

- “I will help you onboard the device and confirm telemetry is really live.”

---

### 7. Super Admin Oversight Agent

**User goal**

- see platform-level business and rollout visibility

**What the agent can do**

- show total organisations
- show active device count
- show tenant/platform risk signals
- show platform maintenance status

**Uses underneath**

- super-admin summary
- org data
- active device counts
- maintenance visibility

**User-facing promise**

- “I will give you platform-wide oversight and health visibility.”

**Important boundary**

- only visible to `super_admin`

---

## Agent = Automation

Yes, this is the important correction:

**Agents are closer to automation/orchestration than to simple feature navigation.**

For Shivex, an agent should usually do some combination of:

- ask for a goal
- ask for a scope
- build a plan
- configure one or more underlying actions
- keep background watch
- show progress
- show result
- suggest next action

That is the real product shape.

---

## What The UI Should Feel Like

The UI should not feel like:

- seven product pages renamed as agents
- a simulator of existing modules
- “click card -> go to page”

It should feel like:

- “tell the system what you want”
- “the system creates a plan”
- “the system activates automation”
- “the system monitors in background”
- “the system brings back outcomes and decisions”

---

## Recommended UI Direction

The best UX shape is:

### Section 1: Outcome Picker

At the top:

- `What do you want to achieve?`

Cards:

- Reduce Energy Cost
- Stop Idle Running Waste
- Maximize Uptime
- Reduce Overconsumption
- Prepare Daily Briefing
- Onboard And Verify Device
- Super Admin Oversight

This is the most important shift.

### Section 2: Agent Plan Builder

When a user clicks a goal, the UI should show:

- what the agent will do
- what inputs are needed
- what actions it will configure
- what outputs it will produce

Example:

`Reduce Energy Cost Agent`
- target reduction: 5%, 10%, 15%
- scope: all machines / plant / selected devices
- cadence: once / daily / weekly
- outputs:
  - schedule report
  - enable monitoring
  - flag top waste devices
  - notify manager on threshold breach

### Section 3: Execution Plan

After the user confirms, show:

- step 1: evaluate fleet baseline
- step 2: identify highest waste devices
- step 3: configure rules / alerts
- step 4: schedule reports
- step 5: activate monitoring

This is where the UI starts to feel intelligent.

### Section 4: Active Automations

Show:

- which plans are active
- which jobs are running
- which reports are ready
- which alerts fired
- which recommendations are waiting

### Section 5: Recommended Next Actions

Show things like:

- `VD00000003 has abnormal current pattern — review before next shift`
- `Waste scan found 3 idle-loss opportunities worth reviewing`
- `Daily ops briefing is ready`
- `Two onboarding flows need telemetry verification`

---

## Best One-Artifact Working Prototype

If a single artifact should explain everything, it should be this:

### Left or top section

- outcome cards

### Middle section

- selected agent plan builder

### Right or lower section

- active automations
- progress
- recommendations
- outputs

That way, the user can understand:

- goal
- plan
- automation
- progress
- result

all in one place.

---

## Wireframe

### Wireframe: Outcome-Driven Agent Workspace

```text
+--------------------------------------------------------------------------------------------------+
| Shivex Agentic Automation                                                                        |
| What do you want to achieve?                                                                     |
+--------------------------------------------------------------------------------------------------+

+--------------------------+--------------------------+--------------------------+------------------+
| Reduce Energy Cost       | Stop Idle Waste          | Maximize Uptime          | Reduce           |
|                          |                          |                          | Overconsumption  |
+--------------------------+--------------------------+--------------------------+------------------+
| Daily Ops Briefing       | Onboard & Verify Device  | Super Admin Oversight    |                  |
+--------------------------+--------------------------+--------------------------+------------------+

+--------------------------------------------------------------------------------------------------+
| Selected Goal: Reduce Energy Cost                                                                |
|                                                                                                  |
| Scope: [All Machines] [Plant] [Selected Devices]                                                 |
| Target: [5%] [10%] [15%]                                                                         |
| Frequency: [One time] [Daily] [Weekly]                                                           |
|                                                                                                  |
| Agent will:                                                                                      |
| - analyze top waste drivers                                                                      |
| - schedule recurring energy report                                                               |
| - activate alert rules for abnormal usage                                                        |
| - monitor progress across selected machines                                                      |
|                                                                                                  |
| [Build Agent Plan]                                                                               |
+--------------------------------------------------------------------------------------------------+

+--------------------------------------------------+-----------------------------------------------+
| Agent Execution Plan                             | Active Automations                            |
|                                                  |                                               |
| 1. Analyze baseline                              | - Energy cost reduction plan active           |
| 2. Rank high-waste devices                       | - Idle waste monitor active                   |
| 3. Create / update alert logic                   | - Daily ops briefing scheduled                |
| 4. Schedule report output                        |                                               |
| 5. Activate monitoring                           |                                               |
+--------------------------------------------------+-----------------------------------------------+

+--------------------------------------------------+-----------------------------------------------+
| Current Results                                  | Recommended Next Actions                      |
|                                                  |                                               |
| - 3 high-waste devices found                     | - Review VD00000003 before next shift         |
| - 1 report scheduled daily at 08:00              | - Approve new overconsumption threshold       |
| - 2 rules activated                              | - Verify telemetry for 2 new devices          |
+--------------------------------------------------+-----------------------------------------------+
```

---

## What Claude Must Build Instead Of The Earlier Version

The next implementation must not be:

- module cards
- page-launch buttons
- “analytics/reporting/waste/rules” relabeled as agents

It must be:

- **goal cards**
- **plan builder**
- **automation execution view**
- **background monitoring view**
- **recommendation output view**

That is the main requirement.

---

## Claude Prompt For The Correct Direction

```text
You are working in the Shivex-Main codebase.

I want a customer-facing agentic automation prototype for Shivex.

Important correction:
- do NOT build agents as renamed product modules like Analytics / Reports / Waste / Rules
- do NOT make it feel like page navigation
- agents should feel like automation/orchestration around user goals

Correct product model:
- user chooses an outcome
- system builds a plan
- system configures actions across the platform
- system monitors in background
- system shows progress, outputs, and recommendations

Build a single self-contained UI artifact that demonstrates this.

Goal-based agent set:
1. Reduce Energy Cost
2. Stop Idle Running Waste
3. Maximize Uptime
4. Reduce Overconsumption
5. Daily Operations Briefing
6. Onboard And Verify Device
7. Super Admin Oversight

The artifact must include:
1. outcome picker cards
2. selected goal / agent plan builder
3. visible execution plan steps
4. active automations section
5. recommendations section
6. outputs/results section
7. role-aware visibility

Most important UX requirement:
- when I click a goal, I should see the workflow then and there
- not just a button to open another existing page
- the prototype can use mocked/dummy data, but the workflow must be believable

The UI should feel like:
- automation
- orchestration
- planning
- monitoring
- follow-through

The UI should NOT feel like:
- module navigation
- renamed pages
- simulator of existing features

Use the current Shivex design language as reference, but create a stronger agentic workflow surface.

Deliverables:
- working one-artifact UI prototype
- clear goal-based flows
- explanation of what is mocked vs real
- local validation steps
```

---

## Final Product Recommendation

If Shivex wants real agents, the product should move toward:

- **goal-based automation agents**

not:

- **feature-labeled assistants**

That is the most important design decision from this exercise.
