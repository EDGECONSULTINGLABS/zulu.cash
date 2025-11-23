# Signer Agent Prompts (Future)

## Status
Not implemented — ZULU is non-custodial.

## If Implemented

### Transaction Review

```
Review this transaction before signing.

Transaction:
- To: {recipient}
- Amount: {amount} ZEC
- Memo: {memo}
- Fee: {fee}

Verify:
- Recipient address valid
- Amount matches intent
- Fee reasonable
- Memo appropriate

Recommend: SIGN | REJECT | REVIEW
```

### Security Warnings

```
Analyze this transaction for security concerns.

Transaction details:
{transaction}

Check for:
- Phishing patterns
- Unusual amounts
- Suspicious memos
- Known bad actors
```
