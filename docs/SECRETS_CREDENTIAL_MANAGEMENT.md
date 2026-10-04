# Secrets and Credential Management

`CredentialManager` resolves credentials through a caller-supplied
`SecretManager`. It accepts only uppercase environment-variable names, so it
cannot resolve arbitrary paths or configuration keys.

`CredentialReference` exposes only a credential name, required flag, and
configuration status. It never contains a secret value and is safe to use in
diagnostics or configuration checks.

Use `CredentialManager.get` only at a trusted adapter boundary. Supply values
through `EnvironmentSecretManager` or another `SecretManager` implementation;
do not place secrets in project configuration, workflow metadata, logs, or
reports. The manager performs no persistence, workflow transition, or network
operation.
