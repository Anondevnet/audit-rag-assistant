---
id: nssc-variable-shadowing
title: not-so-smart-contracts: Variable Shadowing
source_name: not-so-smart-contracts (Trail of Bits / crytic)
source_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/variable%20shadowing/README.md
source_commit: 020dbdbde3e0c2e8de5f3944e7455e438b0995d5
license: Apache-2.0
license_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/LICENSE
copyright: Copyright Trail of Bits and not-so-smart-contracts contributors
modifications: Added front matter, a normalized H1, and an example-file index; README prose unchanged.
---

# not-so-smart-contracts: Variable Shadowing
Variable shadowing occurs when a variable declared within a certain scope (decision block, method, or inner class)
has the same name as a variable declared in an outer scope.

## Attack
This depends a lot on the code of the contract itself. For instance, in the [this example](inherited_state.sol), variable shadowing prevents the owner of contract `C` from performing self destruct

## Mitigation
The solidity compiler has [some checks](https://github.com/ethereum/solidity/issues/973) to emit warnings when 
it detects this kind of issue, but [it has known examples](https://github.com/ethereum/solidity/issues/2563) where 
it fails.

## Example files in upstream

- `inherited_state.sol`


## Source notice

Adapted from not-so-smart-contracts (Trail of Bits / crytic) (https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/variable%20shadowing/README.md), licensed under the Apache License 2.0. Modified: front matter, heading normalization, example-file index. See data/licenses/not-so-smart-contracts-LICENSE.
