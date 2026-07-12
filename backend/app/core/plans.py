"""
app/core/plans.py
===================
Per-tenant plan limits. `tenant_plan` was read and logged by
TenantAuthMiddleware (bound to request.state.tenant_plan on every request)
but never actually checked against anything — billing tiers exist in the
data model (tenants.plan) with no functional teeth (audit #35).

Scope: this wires real enforcement into exactly one concrete, well-understood
quota (max active users per tenant, checked at user-provisioning time) as
the proof that the mechanism works end-to-end, rather than inventing a
speculative feature-flag framework nothing calls yet. Extending this to
other quotas (storage, API rate, module access) means adding new keys to
PLAN_LIMITS and a check at the relevant creation endpoint — the pattern is
established, but the additional checks it would ideally be applied to
(the ones the audit's "usage quotas" wording gestures at more broadly)
haven't been added.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    max_users: int | None  # None = unlimited


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(max_users=5),
    "professional": PlanLimits(max_users=25),
    "enterprise": PlanLimits(max_users=None),
}

_DEFAULT_PLAN = "free"


def get_plan_limits(plan: str | None) -> PlanLimits:
    """Unrecognized/missing plan values fail closed to the most
    restrictive tier rather than silently granting unlimited access."""
    return PLAN_LIMITS.get(plan or _DEFAULT_PLAN, PLAN_LIMITS[_DEFAULT_PLAN])
