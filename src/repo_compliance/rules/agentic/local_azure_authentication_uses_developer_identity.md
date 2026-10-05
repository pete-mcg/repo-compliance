# Rule

When an application is run or tested locally and connects to Azure resources, it must **always** authenticate using the developer's own Microsoft Entra user account.

Trace the credential supplied to each local Azure client; an environment toggle is supporting evidence only.

## Pass

Examples:
- `AzureCliCredential` after `az login`.
- `DefaultAzureCredential` or `ChainedTokenCredential` shown to resolve to the developer's login.
- Local tests use only emulators or fakes.

## Fail

Examples:
- Any local Azure path uses an identity other than the developer's Entra user account.
- Account key, SAS, or credential-bearing connection string.
- Service principal secret or certificate.
- Managed/workload identity without a local developer-user option, or a shared account.

