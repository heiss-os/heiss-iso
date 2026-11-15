# How security reviews are done

The checklist is in `.claude/agents/security-reviewer.md`; this page says where the method comes from and what it does not do.

## Sources

The method was informed by public security-audit practice: the Trail of Bits security-audit skills for Claude Code (<https://github.com/trailofbits/skills>, read on 2026-11-15, licence CC-BY-SA-4.0), and general guidance on threat modelling, differential review, variant analysis and secure defaults. The ideas we took are: rank the work by risk and not by size, follow attacker input from source to sink, search the whole tree for every variant of a bug once one is found, look at insecure defaults, check a suspected bug against the code that may already stop it before reporting it, and rate severity by a written rubric.

**No code or text was copied and nothing from that repository was installed, enabled or run.** The repository was read through the GitHub API as data only; the checklist is written in our own words and adapted to Heiss OS (the root helper on D-Bus with polkit, signed packages from our own repository, GRUB scripts, systemd units, Qt apps, GitHub Actions that publish packages, the ISO build).

## What it is and is not

An automated read-only review by a model, run before a pull request that touches privilege and once over the existing privileged code. It finds mistakes a reader can see in the source. It does not run the helper under polkit, does not fuzz, does not test a real system and can miss things; a clean report is not a proof. Findings of HIGH and MEDIUM severity are fixed before the change is merged (in the same pull request for a diff review, in a separate small one for an audit).
