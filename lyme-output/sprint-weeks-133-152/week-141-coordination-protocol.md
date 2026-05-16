# Week 141 — Specialist Coordination Protocol

**Theme**: Prevent specialist systems from becoming agent spaghetti.

## Message Protocol

| Field | Type | Description |
|-------|------|-------------|
| msg_id | str | Unique message ID |
| msg_type | MessageType | plan, retrieve, generate_patch, critique, verify, state_update, conflict, escalation, stop |
| source | SpecialistRole | The specialist that sent the message |
| target | SpecialistRole | The intended recipient (None = broadcast) |
| payload | dict | The message content |
| confidence | float | 0.0-1.0 |
| in_response_to | str | Optional parent message ID |
| failure_labels | List[str] | Any failure conditions |

## State Handoff Protocol

1. Source writes result to **Blackboard**
2. Source sends **message** to target via message queue
3. Target reads from Blackboard (not from message payload)
4. Target writes its result to Blackboard
5. Router checks for stop conditions

This prevents: message loss, duplicate processing, out-of-order delivery.

## Uncertainty Handoff

When a specialist has confidence < 0.3:
- Sets `failure_labels: ["low_confidence"]` in message
- Router re-routes to different specialist or escalates

## Evidence Handoff

Evidence (file contents, search results, git history) is never passed in messages.
All evidence is written to Blackboard and referenced by key.

## Files Created
- `src/lyme_model/specialists/coordinator.py` — Message protocol, Blackboard, Router, Conflict Resolution, Orchestrator
