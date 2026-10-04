# Asset Packager

`AssetPackagerDTO` は利用可能なアーティファクト参照と、生成済みアセットの有無を診断します。参照の一覧は `WorkflowContext.artifacts` から読み取ります。

パッケージ作成は行わず、`package_created` は常に `false` です。
