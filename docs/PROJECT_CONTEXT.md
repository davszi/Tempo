# Project context

This starter demonstrates a project-owned documentation site built by a version-pinned shared kit. It has no application runtime or performance results.

## Read first

Follow the [task routes](../AGENTS.md#read-before-the-relevant-action) before the action they govern.

## Repository map

- `.docs-kit/`: initialize the shared-kit Git submodule at the project's reviewed revision.
- `docs/site/site.toml`: site identity, source repository/ref and navigation.
- `docs/topics/home/index.md`: rendered landing page and automatic site map.
- `docs/topics/guide/guide.md`: canonical starter architecture and adoption checklist.
- `docs/topics/guide/index.md`: human-facing visual authoring guide.
- `docs/open/OPEN.md`: unfinished-work routes.
- `docs/worklog.md`: append-only chronology.
- `.build/docs/`: ignored generated output, never source.

## Build and review

Run from the project root after initializing the submodule. Use Python 3.12 or the later version supported by the pinned kit.

```bash
python -m pip install -r .docs-kit/requirements.txt
python .docs-kit/docsite.py build --project .
python .docs-kit/docsite.py build --project . --check
python .docs-kit/docsite.py lint --project .
```

For an iteration, append `--page guide` to build; this does not validate unrelated output. For browser review:

```bash
python -m http.server 8321 --bind 127.0.0.1 --directory .build/docs
```

Open `http://127.0.0.1:8321/html/guide.html` through the approved browser surface. Check the listener's owner before reuse. Review wide, narrow and paired reading; inspect keyboard focus, reduced motion, no-JavaScript fallback and print. Consult the kit README for shared-engine development checks; Node.js is needed only for applicable JavaScript checks, not ordinary content builds.

## Project choices still required

Replace `https://github.com/example/project` in site configuration. Choose the source ref and actual hosting/deployment policy. No hosting target, release tag, published URL or project test result is assumed by the starter.

## Documentation index

[Documentation reading index](index.md) · [Starter topic record](topics/guide/guide.md) · [Open work](open/OPEN.md) · [Worklog](worklog.md).
