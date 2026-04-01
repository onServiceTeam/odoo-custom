# onService Operations — Core

Security groups and foundation for all `ons_ops_*` modules.

## What This Module Does

- Creates the **onService Operations** category on the user form
- Defines three security groups in a hierarchy:
  - **Agent** — base role for all operations employees
  - **Manager** — implies Agent; adds team management access
  - **Administrator** — implies Manager; adds system configuration access
- Reserves the `ons_ops_core.*` config parameter namespace

## Upgrade Safety

| Concern | Status |
|---------|--------|
| Stock model changes | None |
| Stock view changes | None |
| Enterprise conflicts | None — uses dedicated `ir.module.category` |
| OCA compatibility | Full — standard group hierarchy pattern |

## Depends

- `base`
