# Dataset and licensing

This repository ships a small, license-cleared knowledge base of *educational* smart-contract weakness write-ups. It is not a corpus of professional firm audit reports, and it is not a substitute for an audit.

Every document records its upstream URL (pinned to a commit), license, and copyright in YAML front matter. The same records are in [`data/MANIFEST`](data/MANIFEST) (JSON).

## What is included

| Source | License (verified from the repo `LICENSE` file) | Count | Pinned commit |
| --- | --- | --- | --- |
| [SWC Registry](https://github.com/SmartContractSecurity/SWC-registry) | MIT | 37 | `1b6227074ecd180b374e4844153afdda0332f979` |
| [not-so-smart-contracts](https://github.com/crytic/not-so-smart-contracts) | Apache-2.0 | 12 | `020dbdbde3e0c2e8de5f3944e7455e438b0995d5` |

Upstream license texts are copied at:

- [`data/licenses/SWC-registry-LICENSE`](data/licenses/SWC-registry-LICENSE)
- [`data/licenses/not-so-smart-contracts-LICENSE`](data/licenses/not-so-smart-contracts-LICENSE)

Modifications are limited to: YAML front matter, a normalized heading, removal of the repeated SWC “no longer maintained” banner (the fact is preserved in each document’s source notice and in this file), and an example-file index for the Apache-2.0 READMEs. Upstream README / SWC entry prose is otherwise unchanged. Large third-party contract dumps that sit beside those READMEs (for example full `DAO_source_code` trees) are *not* copied into this repo.

The SWC Registry itself states that it is no longer actively maintained (last substantive update 2020). Treat the content as historical educational material and prefer current guidance such as the [EEA EthTrust Security Levels specification](https://entethalliance.org/specs/ethtrust-sl/) when reviewing live code.

## What is excluded, on purpose

- **Code4rena** findings and reports. Code4rena’s Terms of Service forbid scraping or bulk download and forbid using C4 content to train, fine-tune, *or evaluate* models, including creating embeddings or derived datasets, except via a designated API or written permission. See https://docs.code4rena.com/legal/terms-of-service
- **Sherlock** audit reports. Public links are posted with protocol-team permission; reuse rights sit in engagement agreements, not a blanket license. See https://sherlock.xyz/terms-of-service
- **Solodit / Cyfrin** findings. Deferred until the current API terms are read and confirmed. See https://www.cyfrin.io/terms-and-conditions
- Third-party Hugging Face scrapes of the above.

## Regenerating the corpus

```bash
git clone --depth 1 https://github.com/SmartContractSecurity/SWC-registry.git /tmp/audit-rag-sources/SWC-registry
git clone --depth 1 https://github.com/crytic/not-so-smart-contracts.git /tmp/audit-rag-sources/not-so-smart-contracts
python scripts/build_corpus.py --sources /tmp/audit-rag-sources
```

Then re-check `data/MANIFEST` and the copied `LICENSE` files before committing.
