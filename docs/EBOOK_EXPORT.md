# eBook Export

`EBookExportDTO` は電子書籍向けの納品適格性を診断します。

`WorkflowContext.metadata.ebook_export` に `format` と `reading_direction` を指定してください。共通の承認・品質・生成条件と仕様がそろったときだけ `ready` になります。電子書籍ファイルの生成や配信は行いません。
