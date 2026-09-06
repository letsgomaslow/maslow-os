# Maslow Connect

Maslow Connect gives supported AI tools one consistent, permission-controlled connection to applications you authorize. It keeps provider keys and MCP configuration details out of your AI tool configuration.

Open **Setup > Maslow Connect** from the Maslow OS menu, or run:

```bash
omarchy connect open
```

## Set up this device

Run:

```bash
omarchy connect setup
```

Maslow OS shows a short-lived code and opens the Maslow Connect website. Sign in, approve this device, and then return to the terminal. Connecting Maslow Connect does not sign you into Codex, Claude Code, Hermes, or an external application automatically.

Connect GitHub, Gmail, Google Calendar, Google Drive, Slack, or Notion from the Apps page. Each account belongs to your Maslow Connect user. The service may show Composio on an external provider consent screen during the pilot.

## Give an AI tool access

List the available adapters:

```bash
omarchy connect agent list
```

Enable one installed tool explicitly:

```bash
omarchy connect agent enable codex
omarchy connect agent enable claude-code
omarchy connect agent enable hermes
```

New tools receive no application access automatically. In the Maslow Connect app, choose which connected applications each tool may read. Write access is a separate opt-in and does not include destructive, financial, account-administration, credential, or irreversible communication actions in the first release.

## Check or remove access

```bash
omarchy connect status
omarchy connect doctor codex
omarchy connect agent disable codex
omarchy connect logout
```

Disabling one AI tool removes only that tool's Maslow Connect entry and grant. It does not disconnect your applications from other enabled tools. Signing out removes this device's local Maslow credential; it does not sign you out of the external applications themselves.

Maslow Connect diagnostics do not call an external application and do not print provider tokens, tool arguments, or tool results.

