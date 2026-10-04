# Web Export

`WebExportDTO` は Web 公開向けの納品適格性を診断します。

`WorkflowContext.metadata.web_export` に `format` と `width` を指定してください。共通の承認・品質・生成条件と仕様がそろったときだけ `ready` になります。Web への公開やアップロードは行いません。
