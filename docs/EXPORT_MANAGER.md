# Export Manager

`ExportManagerDTO` はプロジェクトと対象ページの共通納品適格性を表します。`page_count` は常に 1 であり、複数ページの一括実行を受け付けません。

適格性には、`Generated` アーティファクト、`QualityChecked` アーティファクト、`Approved` 状態が必要です。`export_performed` は常に `false` です。
