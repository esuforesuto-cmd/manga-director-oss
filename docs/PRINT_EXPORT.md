# Print Export

`PrintExportDTO` は印刷用の納品適格性を診断します。

`WorkflowContext.metadata.print_export` に `trim_size` と `dpi` を指定してください。共通の承認・品質・生成条件と仕様がそろったときだけ `ready` になります。印刷ファイルは生成しません。
