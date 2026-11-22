---
id: nssc-integer-overflow
title: not-so-smart-contracts: Integer Overflow
source_name: not-so-smart-contracts (Trail of Bits / crytic)
source_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/integer_overflow/README.md
source_commit: 020dbdbde3e0c2e8de5f3944e7455e438b0995d5
license: Apache-2.0
license_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/LICENSE
copyright: Copyright Trail of Bits and not-so-smart-contracts contributors
modifications: Added front matter, a normalized H1, and an example-file index; README prose unchanged.
---

# not-so-smart-contracts: Integer Overflow

It is possible to cause `add` and `sub` to overflow (or underflow) on any type of integer in Solidity.  

## Attack Scenarios

- Attacker has 5 of some ERC20 token. They spend 6, but because the token doesn't check for underflows,
they wind up with 2^256 tokens.

- A contract contains a dynamic array and an unsafe `pop` method. An attacker can underflow the length of
the array and alter other variables in the contract.

## Mitigations

- Use openZeppelin's [safeMath library](https://github.com/OpenZeppelin/openzeppelin-solidity/blob/master/contracts/math/SafeMath.sol)
- Validate all arithmetic

## Examples

- In [integer_overflow_1](interger_overflow_1.sol), we give both unsafe and safe version of
the `add` operation.

- [A submission](https://github.com/Arachnid/uscc/tree/master/submissions-2017/doughoyte) to the Underhanded Solidity Coding Contest that explots the unsafe dynamic array bug outlined above

## Example files in upstream

- `integer_overflow_1.sol`


## Source notice

Adapted from not-so-smart-contracts (Trail of Bits / crytic) (https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/integer_overflow/README.md), licensed under the Apache License 2.0. Modified: front matter, heading normalization, example-file index. See data/licenses/not-so-smart-contracts-LICENSE.
