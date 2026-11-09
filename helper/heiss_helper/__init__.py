"""heiss-helper: privileged executor for Heiss OS (system D-Bus + polkit).

It accepts only structured requests. Every parameter is validated against an
allowlist built from root-owned manifests; no client-supplied command, path or
file content is ever executed or written.
"""
__version__ = "0.1.0"
