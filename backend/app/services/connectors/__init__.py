"""Job portal connector system — pluggable, one file per portal.

Every connector is a small adapter with three things:

  1. A `can_auto_apply() -> bool` — True if the portal supports full automation
     (API-based apply). False means "prepare everything + open the page."
  2. An `is_configured(portal_profile: dict) -> bool` — checks whether the
     user has set up the credentials / profile needed.
  3. An `apply(job: dict, master_resume: dict, portal_profile: dict) -> dict`
     returning {"applied": True/False, "method": "auto"|"manual",
     "apply_url": "...", "message": "..."}.

To add a new connector:
  1. Drop a new file in this folder (e.g. `myportal.py`) with those three
     functions, following lever.py or linkedin.py as a template.
  2. Register it in `registry.py`'s CONNECTORS list with the portal_name
     that matches the portal_profiles table.
That's it — the router and UI pick it up automatically.
"""
