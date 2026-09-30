# Rule

When an application is run or tested locally and connects to Azure resources, it must authenticate using the developer's own Microsoft Entra user account.

## Pass

Every local path to Azure uses the signed-in developer's Entra identity.

Examples:
- `AzureCliCredential` after `az login`.
- `DefaultAzureCredential` or `ChainedTokenCredential` shown to resolve to the developer's login.
- Local tests use only emulators or fakes.

Trace the credential supplied to each local Azure client; a mode toggle is supporting evidence only.

## Fail

Any local Azure path uses an identity other than the developer's Entra user account.

Examples:
- Account key, SAS, or credential-bearing connection string.
- Service principal secret or certificate.
- Managed/workload identity without a local developer-user option, or a shared account.

## Uncertain

Azure is used locally, but its credential path is unclear or evidence conflicts.

Examples:
- Azure Identity is a dependency, but the credential used by the local client is unknown.
- Local configuration or a credential chain has unresolved behavior.

## Evidence

- Pass: cite local setup and the credential supplied to each Azure client.
- Fail: cite the non-compliant credential and its local use.
- Uncertain: cite conflicting or unresolved authentication evidence.
