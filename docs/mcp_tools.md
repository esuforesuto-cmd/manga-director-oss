# MCP Tools

All tool inputs are Pydantic-validated JSON schemas. Page tools accept one
`project_id` and one `page_number`; `metadata` carries tool-specific input.
They always delegate through `WorkflowEngine` or `WorkflowCoordinator`.

## Project and Chapter

- `create_project`
- `list_projects`
- `get_project`
- `delete_project`
- `get_project_status`
- `run_project`
- `resume_project`
- `run_chapter`
- `get_chapter_status`

## Page

- `design_page`
- `review_page`
- `create_storyboard`
- `improve_dialogue`
- `build_prompt`
- `generate_image`
- `review_quality`
- `check_continuity`
- `approve_page`
- `get_page_status`

`approve_page` requires a `QualityChecked` Page and explicit `approved_by`
input. Project and Chapter run tools delegate their existing one-page scheduling
rules; no MCP tool may approve automatically or create multiple Pages.

Inspect the actual schemas with:

```bash
manga-director mcp tools
```
