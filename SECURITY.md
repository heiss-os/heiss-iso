# Security policy

Heiß OS is an early-stage project. Please report vulnerabilities privately, not in public issues.

## How to report

Use GitHub's private vulnerability reporting: open the repository `heiss-os/heiss-iso`, go to the **Security** tab and choose **Report a vulnerability**. (The project owner must have this feature switched on in the repository settings; if the button is missing, open an issue that says only "security contact needed" and no details, and the owner will reply.)

Please include what you found, how to reproduce it, the version or commit, and the impact you expect. Do not include real personal data.

## What to expect

The project is run by a very small team. We aim to acknowledge a report within a week and to tell you what we decided. There is no bug bounty.

## Scope

In scope: the privileged helper (`helper/`), the profile engine (`core/`), packaging and installer scripts, and the files that end up in the image. See `docs/SECURITY-MODEL.md` for what the helper is meant to guarantee and its known limits.

Out of scope: vulnerabilities in upstream software (Arch Linux, KDE, Calamares, Linux): report those upstream; attacks that need root access already; findings that only apply to modified builds.

## Supported versions

There is no stable release yet. Only the current `main` branch is supported.
