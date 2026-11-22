---
id: nssc-forced-ether-reception
title: not-so-smart-contracts: Contracts can be forced to receive ether
source_name: not-so-smart-contracts (Trail of Bits / crytic)
source_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/forced_ether_reception/README.md
source_commit: 020dbdbde3e0c2e8de5f3944e7455e438b0995d5
license: Apache-2.0
license_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/LICENSE
copyright: Copyright Trail of Bits and not-so-smart-contracts contributors
modifications: Added front matter, a normalized H1, and an example-file index; README prose unchanged.
---

# not-so-smart-contracts: Contracts can be forced to receive ether

In certain circunstances, contracts can be forced to receive ether without triggering any code. This should be considered by the contract developers in order to avoid breaking important invariants in their code.

## Attack Scenario

An attacker can use a specially crafted contract to forceful send ether using `suicide` / `selfdestruct`:

```solidity
contract Sender {
  function receive_and_suicide(address target) payable {
    suicide(target);
  }
}
```

## Example

- The MyAdvancedToken contract in [coin.sol](coin.sol#L145) is vulnerable to this attack. It will stop the owner to perform the migration of the contract.

## Mitigations

There is no way to block the reception of ether. The only mitigation is to avoid assuming how the balance of the contract
increases and implement checks to handle this type of edge cases.

## References

- https://solidity.readthedocs.io/en/develop/security-considerations.html#sending-and-receiving-ether

## Example files in upstream

- `coin.sol`


## Source notice

Adapted from not-so-smart-contracts (Trail of Bits / crytic) (https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/forced_ether_reception/README.md), licensed under the Apache License 2.0. Modified: front matter, heading normalization, example-file index. See data/licenses/not-so-smart-contracts-LICENSE.
