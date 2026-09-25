# Rule

When an application is run or tested locally and connects to Azure resources, it must authenticate using the developer's own Microsoft Entra user account.

## Pass

Return `pass` only when **every** local path that connects to Azure resources uses the signed-in developer's identity. Accept patterns such as:

- developers run `az login` and the application uses `AzureCliCredential`;
- local mode uses `DefaultAzureCredential` with documentation or configuration showing that it resolves to the developer's login;
- local mode uses `ChainedTokenCredential` with a developer-user credential such as `AzureCliCredential`;
- local tests use only local emulators or fakes and do not connect to Azure resources.

A toggle such as `AZURE_DEV_MODE` is useful evidence but is not required. The authentication behaviour is what matters.

## Fail

Return `fail` when **at least one** local path connects to an Azure resource using anything other than the developer's own Entra user account. Examples include:

- account keys, access keys, shared access signatures, or credential-bearing connection strings;
- a client secret or certificate for a service principal;
- managed identity or workload identity with no local developer-user alternative;
- a shared account or any other non-personal identity.

Also return `fail` when the repository clearly supports local connections to Azure resources but provides no path that authenticates as the developer.

## Uncertain

Return `uncertain` when the repository appears to connect to Azure resources but the local authentication path cannot be established, or when the evidence conflicts. Do not infer compliance from an Azure Identity package dependency or a credential class name alone; trace the credential used by the locally configured Azure client.

## Evidence

- For a pass, cite the lines that establish the local-development path and the credential supplied to each Azure client.
- For a failure, cite the non-compliant credential or configuration and the evidence that it is used locally.
