# Unit of Work

`DatabaseRepository.unit_of_work()` exposes `commit`, `rollback`, and `close`.
It commits after a successful context and rolls back whenever an exception
escapes. Repository `save` writes aggregate and query rows in one transaction.
