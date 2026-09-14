"""Explicit ordered registry of enabled compliance rules."""

from repo_compliance.rules.deterministic.codeowners_present import (
    RULE as CODEOWNERS_PRESENT,
)
from repo_compliance.rules.deterministic.deploy_workflow_present import (
    RULE as DEPLOY_WORKFLOW_PRESENT,
)
from repo_compliance.rules.deterministic.main_branch_deletion_protected import (
    RULE as MAIN_BRANCH_DELETION_PROTECTED,
)
from repo_compliance.rules.deterministic.no_critical_dependabot_alerts import (
    RULE as NO_CRITICAL_DEPENDABOT_ALERTS,
)
from repo_compliance.rules.deterministic.no_key_based_authentication import (
    RULE as NO_KEY_BASED_AUTHENTICATION,
)

RULES = (
    MAIN_BRANCH_DELETION_PROTECTED,
    CODEOWNERS_PRESENT,
    DEPLOY_WORKFLOW_PRESENT,
    NO_CRITICAL_DEPENDABOT_ALERTS,
    NO_KEY_BASED_AUTHENTICATION,
)
RULE_IDS = frozenset(rule.id for rule in RULES)
