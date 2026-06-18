# Issue Tracker

Issues are tracked on **GitHub Issues** via the [`gh` CLI](https://cli.github.com/).

## Prerequisites

- A GitHub remote must be configured for this repo: `git remote add origin <repo-url>`
- The `gh` CLI must be installed and authenticated: `gh auth login`

## Usage

Skills (`to-issues`, `triage`, `to-prd`) use `gh issue create`, `gh issue list`, `gh issue edit`, etc.

If the repo has no GitHub remote or `gh` is not installed, issues cannot be written until those are set up.
