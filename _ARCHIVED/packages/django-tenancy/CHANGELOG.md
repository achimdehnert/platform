# Changelog — django-tenancy

All notable changes to this package are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.2.0] — Unreleased

### Security
- **Cross-org IDOR fix**: `SubdomainTenantMiddleware` resolved tenants from the
  subdomain and the `X-Tenant-ID` header *without* verifying organization
  membership (only the session path checked). An authenticated user could enter
  a foreign org's context — and read its data — via `acme.<host>` or
  `X-Tenant-ID: <uuid>`. Both paths now enforce `Membership` for authenticated
  users. **Behavior change**: authenticated non-members are denied (tenant
  stripped). Anonymous public access is unchanged (backward-compatible).
- Header path now also rejects inactive organizations (parity with subdomain).

## [0.1.0] — Unreleased

### Added
- Initial release.
