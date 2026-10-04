# Creative Workspace Foundation

v4のCreative Workspace Foundationは、既存のProject、Repository、
`WorkflowContext`からUnified Workspace、Session、Snapshot、Timeline、Summaryを
投影するApplication Serviceです。`V4FoundationService.workspace()`は読み取り
専用であり、Workspaceを保存せず、Sessionを開始せず、SnapshotやTimelineを保持
せず、Workflow状態を変更しません。

Repository Interfaceは変更されません。すべての証跡は既存の
`ProjectRepository.load()`経由で取得され、StateMachineだけが遷移を検証します。
