# agent-core/prompts

System prompts for ZULU's agents.

## Prompt Files

- `live.md`: Prompt for Live Agent (conversation memory)
- `ledger.md`: Prompt for Ledger Agent (transaction scanning)
- `signer.md`: Prompt for Signer Agent (optional cold wallet)

## Design Principles

- **Separation of concerns**: Each agent has distinct responsibilities
- **Privacy-first**: Prompts emphasize local processing and data minimization
- **Zero correlation**: Live agent never sees ledger data; ledger agent never sees conversation data

## Usage

These prompts are loaded by the respective agents at runtime. They define:
- Agent role and capabilities
- Privacy constraints
- Output format expectations
