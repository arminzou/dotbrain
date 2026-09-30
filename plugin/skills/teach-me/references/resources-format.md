# RESOURCES.md Format

`RESOURCES.md` is the curated set of trusted sources for this project. Group knowledge under one heading per topic, plus a Shared heading for sources several topics use. Knowledge for explainers should be drawn from here, not from parametric guesses. Wisdom comes from the communities listed here.

## Structure

```md
# {Project} Resources

## Knowledge

### Production .NET

- [Microsoft Learn: Handle errors in ASP.NET Core APIs](https://learn.microsoft.com/aspnet/core/fundamentals/error-handling)
  Primary source for `AddProblemDetails`, exception handling, and ASP.NET Core's built-in behavior. Use for: safe, predictable API errors.

### Azure operations

- [Microsoft Learn: Azure Container Apps revisions](https://learn.microsoft.com/azure/container-apps/revisions)
  Revision and replica scope rules. Use for: predicting what a deployment change creates.

### Shared

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
  The HTTP standard for methods and status codes. Use for: any topic that reasons about HTTP.

## Wisdom (Communities)

- [r/dotnet](https://www.reddit.com/r/dotnet/)
  Active .NET practitioner community. Use for: production trade-offs the docs leave open.
```

The `### ` headings under Knowledge match the topics in `MISSION.md`.

## Rules

- **High-trust only.** Prefer primary sources, recognised experts, peer-reviewed work, and communities with strong moderation. If a resource is marketing dressed as education, leave it out.
- **Annotate every entry.** A bare link is useless in three months. Add one line: what it covers and when to reach for it.
- **Group by Knowledge / Wisdom.** Mirrors the philosophy in [SKILL.md](../SKILL.md). It is fine for a resource to appear in only one group.
- **Surface gaps explicitly.** If no good resource exists for an area the mission needs, write a `## Gaps` section listing what is missing. This drives future search.
- **Prune ruthlessly.** A resource that turned out to be wrong, shallow, or off-mission should be removed, not buried. Better five sharp sources than thirty mediocre ones.
- **Record community preferences.** If the user has opted out of joining communities, note it here so future sessions don't keep proposing them.
