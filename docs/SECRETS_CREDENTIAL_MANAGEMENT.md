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

## OpenAI real-image execution

The V7-03 LocalFile CLI path resolves exactly `OPENAI_API_KEY` at the private
Provider boundary and only for the lifetime of one explicitly authorized
execution. The key is checked, together with availability of the existing
`.[openai]` optional package, before a durable Provider attempt is admitted.
Missing package, missing key, invalid Provider selection, or invalid human
authorization therefore fails closed without network use or attempt
consumption.

Never put the key in `config.yaml`, Project or Page data, workflow metadata,
LocalFile evidence or journals, diagnostics, logs, command arguments, or test
fixtures. `--authorized-by` is a durable non-secret human identity; it must not
contain an email address, path, URL, credential name, token, or secret value.

After Provider start, an unknown result is preserved as recovery-required
evidence. Do not retry, create a replacement attempt, or switch Providers,
because the external image and cost may already exist.
