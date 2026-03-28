# Factor Lifecycle

## Purpose

The factor layer is not only a calculator. It is the minimal engineering base for factor research, factor management, and future alpha mining.

## Core Responsibilities

The factor layer is responsible for:

1. extracting factor signals from `market_panel`
2. standardizing factor outputs
3. validating dependencies
4. exporting factor diagnostics
5. managing factor metadata and lifecycle status

## Lifecycle States

Supported states:

- `draft`
- `testing`
- `active`
- `deprecated`

Recommended interpretation:

- `draft`: new idea, not ready for normal experiments
- `testing`: usable for controlled research
- `active`: standard factor candidate
- `deprecated`: kept for compatibility, but should not be enabled by default

## Standard Add-Factor Workflow

1. Add a standalone function in `technical.py` or `fundamental.py`
2. Register the function with `@register_factor(...)`
3. Provide complete metadata:
   - name
   - group
   - description
   - required_columns
   - direction
   - min_history
   - status
   - version
   - category
   - tags
4. Add the factor to `config/factors.yaml`
5. Run:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
```

6. Inspect diagnostics and metadata outputs

## Standard Disable-Factor Workflow

Preferred disable path:

- keep the factor registered
- set `enabled: false` in `config/factors.yaml`

This keeps research history and avoids breaking downstream references.

## Deprecated Factor Workflow

If a factor is deprecated:

- keep the code by default
- mark metadata status as `deprecated`
- default config should not enable it
- if config enables it manually, the build should warn but continue

## Versioning Guidance

Versioning is metadata-based.

Recommended practices:

- simple evolution: update `version`
- behavior-changing variant: register a new name, for example:
  - `mom_20`
  - `mom_20_v2`
  - `mom_20_skip_limit`

Do not overload one factor name with incompatible meanings.

## Factor Families

Factor families can be expressed by:

- `category`
- `tags`
- naming convention

Examples:

- momentum family: `mom_10`, `mom_20`, `mom_60`
- reversal family: `rev_3`, `rev_5`, `rev_10`
- valuation family: `bp`, `ep`

## Alpha Research Hooks

The current structure is intended to support later work on:

- single-factor studies
- factor correlation analysis
- factor elimination
- factor selection
- factor version comparison

These are not fully implemented in this round, but the metadata, lifecycle status, diagnostics, and config-driven build process are designed to support them.
