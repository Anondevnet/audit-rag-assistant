---
id: nssc-wrong-constructor-name
title: not-so-smart-contracts: Wrong Constructor Name
source_name: not-so-smart-contracts (Trail of Bits / crytic)
source_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/wrong_constructor_name/README.md
source_commit: 020dbdbde3e0c2e8de5f3944e7455e438b0995d5
license: Apache-2.0
license_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/LICENSE
copyright: Copyright Trail of Bits and not-so-smart-contracts contributors
modifications: Added front matter, a normalized H1, and an example-file index; README prose unchanged.
---

# not-so-smart-contracts: Wrong Constructor Name

A function intended to be a constructor is named incorrectly, which causes it to end up in the runtime bytecode instead of being a constructor.

## Attack
Anyone can call the function that was supposed to be the constructor.
As a result anyone can change the state variables initialized in this function.

## Mitigations

- Use `constructor` instead of a named constructor

## Examples
- [Rubixi](Rubixi_source_code/Rubixi.sol) uses `DynamicPyramid` instead of `Rubixi` as a constructor
- An [incorrectly named constructor](incorrect_constructor.sol)

## Example files in upstream

- `Rubixi_source_code/Rubixi.sol`
- `incorrect_constructor.sol`


## Source notice

Adapted from not-so-smart-contracts (Trail of Bits / crytic) (https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/wrong_constructor_name/README.md), licensed under the Apache License 2.0. Modified: front matter, heading normalization, example-file index. See data/licenses/not-so-smart-contracts-LICENSE.
