---
id: nssc-unprotected-function
title: not-so-smart-contracts: Unprotected function
source_name: not-so-smart-contracts (Trail of Bits / crytic)
source_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/unprotected_function/README.md
source_commit: 020dbdbde3e0c2e8de5f3944e7455e438b0995d5
license: Apache-2.0
license_url: https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/LICENSE
copyright: Copyright Trail of Bits and not-so-smart-contracts contributors
modifications: Added front matter, a normalized H1, and an example-file index; README prose unchanged.
---

# not-so-smart-contracts: Unprotected function
Missing (or incorrectly used) modifier on a function allows an attacker to use sensitive functionality in the contract.

## Attack Scenario

A contract with a `changeOwner` function does not label it as `private` and therefore
allows anyone to become the contract owner.

## Mitigations

Always specify a modifier for functions.

## Examples
- An `onlyOwner` modifier is [defined but not used](Unprotected.sol), allowing anyone to become the `owner`
- April 2016: [Rubixi allows anyone to become owner](https://etherscan.io/address/0xe82719202e5965Cf5D9B6673B7503a3b92DE20be#code)
- July 2017: [Parity Wallet](https://blog.zeppelin.solutions/on-the-parity-wallet-multisig-hack-405a8c12e8f7). For code, see [initWallet](WalletLibrary_source_code/WalletLibrary.sol)
- BitGo Wallet v2 allows anyone to call tryInsertSequenceId. If you try close to MAXINT, no further transactions would be allowed. [Fix: make tryInsertSequenceId private.](https://github.com/BitGo/eth-multisig-v2/commit/8042188f08c879e06f097ae55c140e0aa7baaff8#diff-b498cc6fd64f83803c260abd8de0a8f5)
- Feb 2020: [Nexus Mutual's Oraclize callback was unprotected—allowing anyone to call it.](https://medium.com/nexus-mutual/responsible-vulnerability-disclosure-ece3fe3bcefa) Oraclize triggers a rebalance to occur via Uniswap.

## Example files in upstream

- `Unprotected.sol`
- `WalletLibrary_source_code/WalletLibrary.sol`


## Source notice

Adapted from not-so-smart-contracts (Trail of Bits / crytic) (https://github.com/crytic/not-so-smart-contracts/blob/020dbdbde3e0c2e8de5f3944e7455e438b0995d5/unprotected_function/README.md), licensed under the Apache License 2.0. Modified: front matter, heading normalization, example-file index. See data/licenses/not-so-smart-contracts-LICENSE.
