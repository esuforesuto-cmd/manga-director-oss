# Image Backend Planning Example

Select image generators through `ImageGeneratorFactory`; `ImageAgent` supplies
only a prompt and receives an `ImageResult`. Any future backend must preserve
the persisted-storyboard-before-image rule and use a mock contract first. See
[Image Backend Backlog](../../docs/IMAGE_BACKENDS.md).
