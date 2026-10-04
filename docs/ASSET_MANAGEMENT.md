# Asset Management Design

## Scope

The v4.3 Asset Management design describes a read-only Asset Catalog, Version
Management, Dependency Tracking, Asset Validation, and Asset Distribution
eligibility model. It is not a new asset repository or distribution service.

## Proposed planning records

| Record | Planning purpose | Prohibited behavior |
| --- | --- | --- |
| Asset Catalog Entry | Identify asset type, owner, provenance, and references. | Creating, deleting, moving, or uploading assets. |
| Asset Version Record | Compare supplied version identifiers and lineage. | Replacing an asset or mutating history. |
| Dependency Record | Show relationships to Pages, scenes, characters, or deliverables. | Resolving, downloading, or rewriting dependencies. |
| Validation Finding | Report supplied metadata or policy mismatches. | Repairing metadata or changing approval status. |
| Distribution Eligibility | Explain human-review prerequisites for a target. | Packaging, signing, uploading, or distributing. |

## Data and compatibility boundary

Future DTOs use Repository reads and supplied metadata only. The existing
Repository interface, Project persistence format, asset paths, Provider and
Backend contracts remain unchanged. Catalog records must redact secret-bearing
locations and preserve provenance rather than fabricate it.

## Review gates

An asset may be described as ready only when its supplied provenance,
version/dependency evidence, required validation, and applicable human review
are present. This is a recommendation, not an approval or publishing action.
