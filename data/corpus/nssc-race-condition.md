---
id: nssc-race-condition
title: not-so-smart-contracts: Race Condition
source_name: not-so-smart-contracts (Trail of Bits / crytic)
source_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/race_condition/README.md
source_commit: 020dbdbde3e0c2e8de5f3944e7455e438b0995d5
license: Apache-2.0
license_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/LICENSE
copyright: Copyright Trail of Bits and not-so-smart-contracts contributors
modifications: Added front matter, a normalized H1, and an example-file index; README prose unchanged.
---

# not-so-smart-contracts: Race Condition
There is a gap between the creation of a transaction and the moment it is accepted in the blockchain.
Therefore, an attacker can take advantage of this gap to put a contract in a state that advantages them.

## Attack Scenario

- Bob creates `RaceCondition(100, token)`. Alice trusts `RaceCondition` with all its tokens. Alice calls `buy(150)`
Bob sees the transaction, and calls `changePrice(300)`. The transaction of Bob is mined before the one of Alice and
as a result, Bob received 300 tokens.

- The ERC20 standard's `approve` and `transferFrom` functions are vulnerable to a race condition. Suppose Alice has
approved Bob to spend 100 tokens on her behalf. She then decides to only approve him for 50 tokens and sends
a second `approve` transaction. However, Bob sees that he's about to be downgraded and quickly submits a
`transferFrom` for the original 100 tokens he was approved for. If this transaction gets mined before Alice's
second `approve`, Bob will be able to spend 150 of Alice's tokens.

## Mitigations

- For the ERC20 bug, insist that Alice only be able to `approve` Bob when he is approved for 0 tokens.
- Keep in mind that all transactions may be front-run

## Examples
- [Race condition](RaceCondition.sol) outlined in the first bullet point above

## Example files in upstream

- `RaceCondition.sol`


## Source notice

Adapted from not-so-smart-contracts (Trail of Bits / crytic) (https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/race_condition/README.md), licensed under the Apache License 2.0. Modified: front matter, heading normalization, example-file index. See data/licenses/not-so-smart-contracts-LICENSE.
