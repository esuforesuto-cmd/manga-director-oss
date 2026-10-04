# v6.0 Marketplace Specification v1.0

## Listing descriptor

`MarketplaceListingDTO` describes an Extension, workflow template, or solution
template using a stable identifier, name, compatibility label, and mandatory
human review marker. `MarketplaceFrameworkReport` validates duplicate-free,
review-required descriptors.

## Publication boundary

The local Marketplace Framework is specification and validation only. It does
not contact a marketplace, publish content, install packages, or mutate a
listing. Marketplace publication remains an explicit maintainer-controlled
operation outside the SDK and workflow runtime.

## Enterprise use

Enterprise deployment may retain approved listing descriptors as review
evidence. Approval, package verification, access control, signing, and remote
publication must be performed by the owning deployment controls.
