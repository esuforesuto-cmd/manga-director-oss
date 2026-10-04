# MCP Prompts

The MCP Prompt catalog is Markdown-backed and ships under
`src/manga_director/prompts/`:

- `design_manga_page`
- `review_manga_page`
- `create_manga_storyboard`
- `optimize_manga_dialogue`
- `build_manga_image_prompt`
- `review_manga_quality`

Prompt text is not embedded in Python code. A prompt may substitute supplied
`project_id` and `page_number` values, but it cannot execute a workflow or
change a Page.

```bash
manga-director mcp prompts
```
