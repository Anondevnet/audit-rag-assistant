---
id: nssc-reentrancy
title: not-so-smart-contracts: Re-entrancy
source_name: not-so-smart-contracts (Trail of Bits / crytic)
source_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/reentrancy/README.md
source_commit: 020dbdbde3e0c2e8de5f3944e7455e438b0995d5
license: Apache-2.0
license_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/LICENSE
copyright: Copyright Trail of Bits and not-so-smart-contracts contributors
modifications: Added front matter, a normalized H1, and an example-file index; README prose unchanged.
---

# not-so-smart-contracts: Re-entrancy
A state variable is changed after a contract uses `call.value`. The attacker uses
[a fallback function](ReentrancyExploit.sol#L26-L33)—which is automatically executed after
Ether is transferred from the targeted contract—to execute the vulnerable function again, *before* the
state variable is changed.

## Attack Scenarios
- A contract that holds a map of account balances allows users to call a `withdraw` function. However,
`withdraw` calls `send` which transfers control to the calling contract, but doesn't decrease their
balance until after `send` has finished executing. The attacker can then repeatedly withdraw money
that they do not have.

## Mitigations

- Avoid use of `call.value`
- Update all bookkeeping state variables _before_ transferring execution to an external contract.

## Examples

- The [DAO](http://hackingdistributed.com/2016/06/18/analysis-of-the-dao-exploit/) hack
- The [SpankChain](https://medium.com/spankchain/we-got-spanked-what-we-know-so-far-d5ed3a0f38fe) hack

## Example files in upstream

- `DAO_source_code/DAO.sol`
- `Reentrancy.sol`
- `ReentrancyExploit.sol`
- `SpankChain_source_code/SpankChain.sol`
- `SpankChain_source_code/SpankChain_Payment.sol`


## Source notice

Adapted from not-so-smart-contracts (Trail of Bits / crytic) (https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/reentrancy/README.md), licensed under the Apache License 2.0. Modified: front matter, heading normalization, example-file index. See data/licenses/not-so-smart-contracts-LICENSE.
