"""Explicit ordered registry of enabled compliance rules."""

from repo_compliance.rules.agentic.artefact_generation_manual_only import (
    RULE as ARTEFACT_GENERATION_MANUAL_ONLY,
)
from repo_compliance.rules.agentic.ci_workflow_targeting_development import (
    RULE as CI_WORKFLOW_ON_PULL_REQUESTS,
)
from repo_compliance.rules.agentic.frontend_build_identifier_visible import (
    RULE as FRONTEND_BUILD_IDENTIFIER_VISIBLE,
)
from repo_compliance.rules.agentic.local_azure_authentication_uses_developer_identity import (
    RULE as LOCAL_AZURE_AUTHENTICATION_USES_DEVELOPER_IDENTITY,
)
from repo_compliance.rules.agentic.no_prohibited_tooling import (
    RULE as NO_PROHIBITED_TOOLING,
)
from repo_compliance.rules.agentic.project_documentation_present import (
    RULE as PROJECT_DOCUMENTATION_PRESENT,
)
from repo_compliance.rules.agentic.source_uses_standard_branch_names import (
    RULE as SOURCE_USES_STANDARD_BRANCH_NAMES,
)
from repo_compliance.rules.deterministic.codeowners_present import (
    RULE as CODEOWNERS_PRESENT,
)
from repo_compliance.rules.deterministic.dependabot_present import (
    RULE as DEPENDABOT_PRESENT,
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
from repo_compliance.rules.deterministic.pull_request_template_present import (
    RULE as PULL_REQUEST_TEMPLATE_PRESENT,
)

RULES = (
    ARTEFACT_GENERATION_MANUAL_ONLY,
    CI_WORKFLOW_ON_PULL_REQUESTS,
    FRONTEND_BUILD_IDENTIFIER_VISIBLE,
    LOCAL_AZURE_AUTHENTICATION_USES_DEVELOPER_IDENTITY,
    NO_PROHIBITED_TOOLING,
    PROJECT_DOCUMENTATION_PRESENT,
    SOURCE_USES_STANDARD_BRANCH_NAMES,
    CODEOWNERS_PRESENT,
    DEPENDABOT_PRESENT,
    DEPLOY_WORKFLOW_PRESENT,
    MAIN_BRANCH_DELETION_PROTECTED,
    NO_CRITICAL_DEPENDABOT_ALERTS,
    NO_KEY_BASED_AUTHENTICATION,
    PULL_REQUEST_TEMPLATE_PRESENT,
)
RULE_IDS = frozenset(rule.id for rule in RULES)
