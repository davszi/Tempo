+++
title = "Catalog & Data"
slug = "opening-catalog"
description = "Understand opening provenance, the learnable-line tree and the four practice tables."
toc = []
components = ["toc", "nav", "filelinks"]
page_css = ["build-sheet.css"]
+++

# Catalog & Data

<section class="card" id="provenance">

## One opening catalog supplies both practice and simulation

<p class="bs-lead">Named Lichess move sequences become a family-and-line catalog; player progress remains separate from that shared content.</p>

<a href="#catalog-provenance">Figure 1</a> separates historical preparation from the catalog read by the current app and simulator.

<figure id="catalog-provenance">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Historical preparation</span><b>Lichess openings</b><small>Named PGN lines were filtered, converted to UCI and classified. The earlier classifier tooling is retired.</small></div>
<div class="bs-arrow"><span>prepare</span></div>
<div class="bs-node"><span class="bs-label">Shared SQLite content</span><b>Families & lines</b><small>Each family has a side. Each line has an identity, move sequence and optional same-family parent.</small></div>
<div class="bs-arrow"><span>read</span></div>
<div class="bs-stack"><div class="bs-part"><h3>Practice app</h3><p>Browses lines and records real demo-player practice separately.</p></div><div class="bs-part"><h3>Offline simulator</h3><p>Reads the catalog to generate synthetic datasets outside app requests.</p></div></div>
</div>
<figcaption><strong>Figure 1.</strong> Arrows mean content preparation or catalog reads, not a currently runnable automatic import service. Source: <a href="docs.topics.opening-library.opening-library.md.html#scope">historical library provenance</a> and <a href="docs.topics.opening-catalog.opening-catalog.md.html#scope">current catalog scope</a>; diagram authored in this page.</figcaption>
</figure>

| Seed-catalog snapshot | Count | Meaning |
|---|---:|---|
| Opening families | 82 | Family-level names and White/Black classification. |
| Stored lines | 2,719 | Named ordered move sequences. |
| Learnable leaves | 1,889 | Lines that no other stored line extends through a parent link. |
| Headings | 830 | Shorter lines extended by children in the same family. |

These are the recorded seed counts, with read-only verification on 2026-11-15, not a promise about every locally modified database. <a href="docs.topics.opening-catalog.opening-catalog.md.html#read-only-seed-verification-on-2026-11-15">Exact input identity and reproduction</a> remain in the catalog record.

A family's side describes its repertoire classification; a session's side describes which moves the player practises. The browser currently uses the family side automatically. Backend/demo callers also support White, Black or Both. Current classification is implemented; catalog choices other than same-family parents and startup migration still await team confirmation.

The <a href="docs.topics.opening-library.opening-library.md.html">Opening Library record</a> preserves historical source/classification and game evidence. Its retired scripts and earlier family counts should not be read as current import instructions. The <a href="docs.topics.opening-catalog.opening-catalog.md.html">catalog record</a> owns current structure and its open questions.

</section>

<section class="card" id="line-tree">

## Move prefixes define the tree; only its leaves start Learning

<p class="bs-lead">A parent is the longest stored move prefix in the same family, even when line names suggest a different grouping.</p>

<a href="#steinitz-tree">Figure 2</a> uses actual seed rows. All displayed children extend the Steinitz Defense prefix; the parent itself is a heading.

<figure id="steinitz-tree">
<div class="bs-node"><span class="bs-label">Ruy Lopez family · root heading · line 2642</span><b>Steinitz Defense</b><p>Stored prefix: <code>e2e4 e7e5 g1f3 b8c6 f1b5 d7d6 d2d4</code></p><small>Not learnable: child lines already include these opening moves.</small></div>
<p class="bs-label" style="text-align:center">↓ same-family move-prefix children ↓</p>
<div class="bs-grid g2">
<div class="bs-part"><h3>Center Gambit</h3><p>Line 2643 · learnable leaf</p><p>Continues with <code>e5d4 e1g1</code>.</p></div>
<div class="bs-part"><h3>Nimzowitsch Attack</h3><p>Line 2644 · learnable leaf</p><p>Continues with <code>c8d7 b1c3 g8f6 b5c6</code>.</p></div>
<div class="bs-part"><h3>Semi-Duras Variation</h3><p>Line 2645 · learnable leaf</p><p>Continues with <code>c8d7 c2c4</code>.</p></div>
<div class="bs-part"><h3>Berlin Defense, Tarrasch Trap</h3><p>Line 2683 · learnable leaf</p><p>Its stored name differs, but its moves extend this same prefix.</p></div>
</div>
<figcaption><strong>Figure 2.</strong> Every child has <code>parent_line_id = 2642</code>; the displayed children are all of this heading's direct children. Arrows mean stored parent links, not chess evaluations. Source: <a href="docs.topics.opening-catalog.opening-catalog.md.html#catalog-and-data-overview-sources">read-only query and seed hash</a>; diagram authored in this page.</figcaption>
</figure>

Learnability is derived from the absence of children rather than stored in a separate flag. Learning refuses a heading; the frontend lists learnable variations. A previously learned line remains reviewable if a later catalog update gives it children. The rule changes which lines can start Learning, not the identity of existing practice history.

Names and ECO codes are not unique keys. The ordered UCI move sequence is a line's permanent identity; catalog upserts retain its line ID. Same-name variations can be distinguished by their moves. These mechanisms and their trade-offs are detailed in <a href="docs.topics.opening-catalog.opening-catalog.md.html#decisions">catalog decisions</a>.

</section>

<section class="card" id="practice-data">

## Four tables connect shared lines to each player's practice

<p class="bs-lead">The catalog is shared; event history and the saved FSRS card belong to a player and line.</p>

<a href="#data-relationships">Figure 3</a> shows references between the tables. The line ID connects history to catalog content; the progress key contains both player and line.

<figure id="data-relationships">
<div role="region" aria-label="Scrollable four-table relationship diagram" tabindex="0" style="overflow-x:auto">
<svg viewBox="0 0 880 450" role="img" aria-labelledby="data-title data-desc" style="display:block;width:100%;min-width:780px;height:auto">
<title id="data-title">The four SQLite tables and their foreign-key references</title>
<desc id="data-desc">Opening lines refer to opening families and optionally to a parent opening line. Practice events and player lines refer to opening lines. Player lines has the composite key player ID and line ID. There is no players table.</desc>
<defs><marker id="data-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#64c6df"/></marker></defs>
<g fill="#132333" stroke="#56758a" stroke-width="1.5"><rect x="30" y="85" width="320" height="105" rx="10"/><rect x="510" y="85" width="320" height="105" rx="10"/><rect x="30" y="310" width="350" height="105" rx="10"/><rect x="510" y="310" width="320" height="105" rx="10"/></g>
<g fill="none" stroke="#64c6df" stroke-width="2" marker-end="url(#data-arrow)"><path d="M510 140 H350"/><path d="M380 335 L510 190"/><path d="M690 310 V190"/><path d="M680 85 V45 H810 V85"/></g>
<g fill="#dcebf3" font-family="sans-serif" font-size="17"><text x="50" y="119" font-weight="700">opening_families</text><text x="530" y="119" font-weight="700">opening_lines</text><text x="50" y="344" font-weight="700">player_lines</text><text x="530" y="344" font-weight="700">practice_events</text></g>
<g fill="#b5c9d7" font-family="sans-serif" font-size="14"><text x="50" y="149">Primary key: family_id</text><text x="50" y="171">Name and family side</text><text x="530" y="149">Primary key: line_id</text><text x="530" y="171">Moves, name and ECO code</text><text x="50" y="374">Primary key: (player_id, line_id)</text><text x="50" y="396">Learned date, review dates and FSRS card</text><text x="530" y="374">Primary key: event_id</text><text x="530" y="396">Player, session, attempt or completion</text><text x="390" y="127">family_id</text><text x="420" y="275">line_id</text><text x="706" y="254">line_id</text><text x="677" y="29">parent_line_id</text></g>
</svg>
</div>
<figcaption><strong>Figure 3.</strong> Arrows point from the referencing table to the referenced row's table. The top loop is the optional same-family parent. There is no account table in this schema. Source: <a href="docs.topics.database-schema.database-schema.md.html">database schema</a> and <a href="docs.topics.opening-catalog.opening-catalog.md.html#catalog-and-data-overview-sources">figure provenance</a>; diagram authored in this page.</figcaption>
</figure>

| Record | What a practice session writes |
|---|---|
| <code style="white-space:nowrap">practice_events</code> | Planner suggestions, submitted move attempts and session completions. A completed Repeating event carries its grade. |
| <code style="white-space:nowrap">player_lines</code> | First Learning adds repertoire progress; completed reviews update the saved card and next due date. Later Learning preserves the existing schedule. |

Active backend sessions and browser-local unfinished lessons are outside these tables; see <a href="whole-flow.html#storage-boundaries">storage boundaries</a>. Recall and stability shown in the app are derived from the saved card, rather than extra database columns.

Recognized older catalog layouts upgrade transactionally at backend startup. Line IDs and practice/progress references are preserved; merged families do not retain separate IDs. The upgrade rolls back if references would break or a family side cannot be determined. The <a href="docs.topics.opening-catalog.opening-catalog.md.html#9-older-databases-are-upgraded-when-the-backend-starts">migration record</a> owns the exact guarantees; the <a href="docs.topics.database-schema.database-schema.md.html">schema record</a> owns every field.

Direct chosen-line reviews do not record a planner suggestion. They and first-mistake hints remain <a href="docs.topics.frontend.frontend.md.html#unresolved-repeating-behavior">unresolved behavior deviations</a>, not accepted new schema requirements. Continue to <a href="review-dataset.html">Review Data & Grading</a> for the separate offline CSV representation.

</section>
