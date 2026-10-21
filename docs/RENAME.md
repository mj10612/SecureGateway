# SecureGateway 1.0.0 rename

On 2026-10-21, SecureMCP was renamed to **SecureGateway**. This is the same
project and repository, with its existing commits, issues, pull requests and tags.
The previous project name is retained here to connect existing links and OSS
maintainer-program applications to the renamed project.

| Identity | Before | After |
| --- | --- | --- |
| Repository | `mj10612/SecureMCP` | `mj10612/SecureGateway` |
| Python distribution | `secure-mcp` | `secure-gateway` |
| Python module | `secure_mcp` | `secure_gateway` |
| CLI / MCP registration | `secure-mcp` | `secure-gateway` |
| Default state directory | `~/.secure-mcp` | `~/.secure-gateway` |
| Environment prefix | `SECURE_MCP_` | `SECURE_GATEWAY_` |
| Gateway headers | `X-SecureMCP-*` | `X-SecureGateway-*` |

## Breaking change

No compatibility aliases or automatic migration are provided. The renamed
snapshot/lock markers and settings ownership records belong to the new product
identity. Old encrypted sessions are not accepted by the new installation.
Code-number preservation remains the default introduced in 0.7.x.

For an existing installation, use the old CLI to stop and uninstall its gateway,
API gateway, or hooks **before** uninstalling the old package. Preserve any data
needed from that installation; this release does not delete old state. Install
the new package from the renamed repository, rerun the relevant gateway/MCP/hook
installation commands and start a new conversation/session. Review the existing
installation documentation for each host. Do not run both automatic gateways on
the same port.

New checkout and installation:

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
secure-gateway --version
secure-gateway gateway install
```

For an existing checkout:

```sh
git remote set-url origin https://github.com/mj10612/SecureGateway.git
```

The GitHub repository was renamed rather than copied. Do not create a replacement
repository at `mj10612/SecureMCP`: that would break the old-address redirect.
Earlier release tags remain unchanged. Reverting a code change does not rename
GitHub or restore external host settings; those actions must be handled separately.
No publication to PyPI is implied by this release or by an installation from Git.
