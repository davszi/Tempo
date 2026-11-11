+++
toc = []
title = "A shared kit keeps each project in control"
brand_sub = "source ownership · evidence · optional depth"
components = ["toc", "nav", "code", "filelinks", "lightbox"]
page_css = ["build-sheet.css"]
math = true
+++

# A shared kit keeps each project in control

<section class="card" id="pipeline">

<!-- slide -->
<p class="slide-eyebrow">Ownership</p>
<p class="slide-title">The project owns its content; the kit is a pinned tool</p>
<p class="slide-lead">Pages, configuration and evidence stay in the project. One reviewed kit revision supplies rules, theme and reader.</p>
<div class="slide-main"><div class="slide-row"><div class="slide-tile is-term"><h4>Project owns</h4><p>topic records and pages · navigation and local assets · evidence and review</p></div><div class="slide-tile"><h4>Pinned submodule</h4><p>rules and templates · build-sheet theme · reader and validation</p></div><div class="slide-tile is-held"><span class="slide-tag">generated</span><h4>Ready to read</h4><p>HTML and local resources · rebuilt, never edited</p></div></div><div class="slide-legend"><span><i></i>authored source</span><span><i class="is-held"></i>generated output; changes flow from source only</span></div></div>
<p class="slide-scope">Illustration of ownership · no measured results</p>
<!-- /slide -->

## Pin the tools, own the content

<p class="bs-lead">A project chooses its shared-kit revision while keeping its pages and configuration in its own repository.</p>

[Figure 1](#fig-pipeline) separates what a project authors from what the kit supplies. The arrows carry inputs into a generated site; editing output does not update either source.

<figure id="fig-pipeline">
<div class="bs-flow" role="img" aria-label="Project pages and configuration enter the pinned shared kit. The kit generates the website. Generated output never becomes source.">
<div class="bs-node bs-teal"><span class="bs-label">Project owns</span><b>Content and choices</b><ul><li>Topic records and pages</li><li>Navigation and local assets</li><li>Evidence and review</li></ul></div>
<div class="bs-arrow"><span>inputs</span></div>
<div class="bs-node bs-violet"><span class="bs-label">Pinned submodule</span><b>Shared documentation kit</b><ul><li>Rules and templates</li><li>Build-sheet theme</li><li>Reader and validation</li></ul></div>
<div class="bs-arrow"><span>build</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Generated</span><b>Ready to read</b><ul><li>HTML and local resources</li><li>Stable public anchors</li><li>Source links</li></ul></div>
<div class="bs-back"><span>×</span> Generated pages do not flow back into source. Change the record, page, configuration or generator, then rebuild.</div>
</div>
<figcaption><b>Figure 1.</b> Follow the arrows from authored inputs to output. This source-authored HTML diagram illustrates ownership; it contains no measured results.</figcaption>
</figure>

<div class="bs-specs"><div><span class="bs-label">Shared rules</span><b>One pinned revision</b></div><div><span class="bs-label">Project content</span><b>Local ownership</b></div><div><span class="bs-label">Generated site</span><b>Rebuilt from source</b></div></div>

</section>

<section class="card" id="knowledge">

## Let a finding settle into one home

<p class="bs-lead">Move durable knowledge to its subject, keep evidence with its producer, and route unfinished work to its owner.</p>

[Figure 2](#fig-knowledge) shows the promotion path. An accepted design still needs an implementation and evidence before it describes tested behavior.

<figure id="fig-knowledge">
<div class="bs-flow" role="img" aria-label="An open question is investigated with retained evidence. Established findings move to a topic record and are explained to human readers.">
<div class="bs-node bs-orange"><span class="bs-label">Unresolved</span><b>Question and acceptance</b><p>One open owner holds the decision and prospective checks.</p></div>
<div class="bs-arrow"><span>investigate</span></div>
<div class="bs-node bs-violet"><span class="bs-label">Producing work</span><b>Protocol and evidence</b><p>Keep inputs, outputs, failures, source pins and reproduction together.</p></div>
<div class="bs-arrow"><span>establish</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Current knowledge</span><b>Record and explanation</b><p>The topic owns the finding. Its page explains the consequence and links to evidence.</p></div>
</div>
<figcaption><b>Figure 2.</b> Promotion changes the knowledge owner without rewriting original evidence. Chronology belongs in the worklog, outside this flow.</figcaption>
</figure>

<div class="bs-grid g2">
<div class="bs-part bs-teal"><span class="bs-label">Record for agents</span><h3>Preserve the exact contract</h3><p>Use plain Markdown for assumptions, accepted requirements, file references and scoped checks.</p></div>
<div class="bs-part bs-violet"><span class="bs-label">Page for people</span><h3>Explain what the finding means</h3><p>Lead with a claim, draw the mechanism and make the evidence useful without exposing a task board.</p></div>
</div>

</section>

<section class="card" id="evidence">

## A check proves the property it exercised

<p class="bs-lead">Keep design decisions, implemented behavior and runtime observations visibly distinct.</p>

The comparison below names the boundary of each evidence kind. A local unit test cannot establish an untested deployment workload.

<div class="bs-checks">
<div class="bs-check"><span class="bs-badge bs-wait">Decided</span><h3>Accepted design</h3><p>Records a chosen requirement and its rationale. It still needs an implementation and acceptance evidence.</p></div>
<div class="bs-check"><span class="bs-badge bs-wait">Local</span><h3>CPU check</h3><p>Establishes the asserted property for its cases and environment. Name its command, inputs and limits.</p></div>
<div class="bs-check"><span class="bs-badge bs-wait">Runtime</span><h3>Observed behavior</h3><p>Qualifies the recorded workload and runtime. It does not automatically cover changed inputs or another environment.</p></div>
</div>

<!-- fold: experiment What a complete experiment records -->

State measured motivation, a strong cheap baseline and acceptance criteria before results. Retain the reproduction command, source revision, environment, input identities, output table with units, verdict, caveats and next step. A failed acceptance check is a result worth preserving.

No benchmark has been run for this starter. These are authoring requirements, not sample performance results.

<!-- /fold -->

</section>

<section class="card" id="layers">

## Keep the argument visible and depth optional

<p class="bs-lead">A reader should understand the claim and verdict with every supporting fold closed.</p>

[Figure 3](#fig-layers) puts the explanation on the visible path. Math, Experiments, Code and Alternatives add detail without becoming prerequisites hidden from the reader.

<figure id="fig-layers">
<div class="bs-flow n2" role="img" aria-label="Visible story contains the question, mechanism, evidence and verdict. Optional layers add derivation, reproduction, source and alternatives.">
<div class="bs-node bs-teal"><span class="bs-label">Always readable</span><b>Question to verdict</b><ul><li>Define the problem</li><li>Draw the mechanism</li><li>Show decisive evidence</li><li>State the consequence</li></ul></div>
<div class="bs-arrow"><span>go deeper</span></div>
<div class="bs-node bs-violet"><span class="bs-label">Optional layers</span><b>Inspect the supporting work</b><ul><li>Derivation and assumptions</li><li>Protocol and raw results</li><li>Real source excerpts</li><li>Rejected alternatives</li></ul></div>
</div>
<figcaption><b>Figure 3.</b> Optional depth branches from a complete visible argument. Both reader columns keep independent layer preferences.</figcaption>
</figure>

<!-- fold: math Count resources without counting copies -->

Let $P$ be the set of resources referenced by pages and $S$ the shared resources needed by the reader. Their union defines the required bundle:

$$
R = P \cup S
$$

A resource used in both sets appears once. This is set notation for packaging, not a measured size or timing claim.

<!-- /fold -->

<!-- fold: code Configure the project identity once -->

`init` writes the title and source repository into the first lines of `docs/site/site.toml` (`--title`, `--repository`); the home label is a project choice. The two lines after them are a real source excerpt: the revision that source links use, and the switch that turns on the chapter reader.

```toml source=docs/site/site.toml#L3-L4
gh_ref = "main"
chapter_reader = true
```

<!-- /fold -->

</section>

<section class="card" id="slides">

<!-- slide -->
<p class="slide-eyebrow">Slide faces</p>
<p class="slide-title">Open a chapter with one slide, then read on</p>
<p class="slide-lead">A slide states the takeaway with one visual. The full chapter follows below it and must stand on its own.</p>
<div class="slide-main"><div class="slide-split is-wide-side"><dl class="slide-factors"><dt>Title<small>the finding</small></dt><dd><span class="slide-chip is-key">a sentence, not a topic</span></dd><dt>Visual</dt><dd><span class="slide-chip">tiles</span><span class="slide-chip">factor grid</span><span class="slide-chip">figure and numbers</span><span class="slide-chip">equation terms</span></dd><dt>Scope line</dt><dd><span class="slide-chip is-alt">what the numbers cover</span></dd><dt>Canvas</dt><dd><span class="slide-chip is-mono">16:9</span><span class="slide-chip">stacks below 720 px</span></dd></dl><div class="slide-stats"><div class="slide-stat"><b>1</b><span>slide per chapter, at most</span></div><div class="slide-stat is-alt"><b>0</b><span>facts that exist only on the slide</span></div></div></div></div>
<p class="slide-scope">Extract any set of slides with docsite.py slides</p>
<!-- /slide -->

## Open a chapter with one slide, then read on

<p class="bs-lead">A slide face summarises its chapter; the chapter remains the complete, readable source of every claim.</p>

Write the face between `<!-- slide -->` and `<!-- /slide -->` at the start of a chapter. The reader shows it as a 16:9 slide at the top of the card, followed by the full chapter. `python docsite.py slides --project . --select guide --out guide` collects the faces into a deck that can be presented or printed.

</section>

<section class="card" id="review">

## Review the page where people will read it

<p class="bs-lead">A successful source check still needs a rendered review of the changed layout.</p>

<div class="bs-grid g2">
<div class="bs-part bs-teal"><span class="bs-label">Wide and paired</span><h3>Use the available width</h3><p>Check readable chart labels, balanced rows, full-width evidence and two-column comparisons. Keep controls next to their result.</p></div>
<div class="bs-part bs-orange"><span class="bs-label">Narrow and accessible</span><h3>Keep every action reachable</h3><p>Check contained tables and equations, keyboard focus, clear labels, touch targets, reduced motion, print and no-JavaScript reading.</p></div>
</div>

### What remains for this adoption

<div class="bs-board">
<div class="bs-row"><span class="bs-state bs-ok">Decided</span><b>Ownership model</b><span>Use a version-pinned shared kit, with project-owned content and navigation.</span></div>
<div class="bs-row"><span class="bs-state bs-wait">Open</span><b>Project identity</b><span>Replace the example repository and choose the source revision used by source links.</span></div>
<div class="bs-row"><span class="bs-state bs-wait">Open</span><b>Integration checks</b><span>Build, check freshness, lint and inspect the consumer's actual output before adoption.</span></div>
</div>

This board describes starter adoption, not completed test execution. The <a href="../topics/guide/guide.md#acceptance-checklist">agent record</a> owns the exact checklist; <a href="../open/OPEN.md">open routing</a> points to it.

</section>

<section class="card" id="choice">

## Choose shared maintenance with a deliberate update point

<p class="bs-lead">A pinned submodule fits projects that need the same visual language without surrendering their own release schedule.</p>

<div class="scroll" role="region" aria-label="Maintenance options; scroll horizontally" tabindex="0" data-reader-horizontal>

| Option | Shared fixes | Project control | Maintenance cost | Verdict |
|---|---|---|---|---|
| Copy the theme into every project | Reapply each fix separately | Direct local edits | Copies can drift | Suitable only for an intentionally independent fork |
| Pinned shared-kit submodule | Adopt a reviewed kit revision | Content, overrides and update timing stay local | Initialize and review each upgrade | Selected for this starter |
| Independently build each site's engine | No common update path | Complete freedom | Maintain reader, checks and theme per project | Use when requirements differ enough to justify it |

</div>

The verdict follows ownership and update behavior, not a measured speed comparison. Keep a kit upgrade reviewable: change the pin, rebuild the consumer and inspect its actual pages.

<!-- fold: dead-end Why a copied reader creates more owners -->

A local copy can be appropriate for a deliberate fork. It stops being a shared component: fixes to keyboard behavior, deep links and saved reading positions must be integrated independently. Record that ownership decision rather than treating the fork as an automatic shared-kit update.

<!-- /fold -->

</section>
