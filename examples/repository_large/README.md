# Selective Repository Reads

Run from a development checkout with `PYTHONPATH=src`:

```text
python examples/repository_large/selective_read.py
```

The optional metadata/page/history helpers avoid forcing a full aggregate read
for simple operational views. Existing Repository consumers do not need to
change.
