# Browser TOAST test plan

This is a branch-based regression plan, not a claim to enumerate every possible
invalid byte sequence. Automated tests use the production engine and UI in the
final standalone document. Only the fictional Dunford tournament is used.

## Automated release gate

Run `scripts/test_browser_toast.py` through the repository's Python environment.
Require zero failures, a complete report, and process exit status zero in both
Chrome and Edge. A missing result is a failure, never an implicit pass.

| Area | Inputs / scenario | Expected outcome |
| --- | --- | --- |
| Python references | Real two-division Dunford and a controlled single division with dual emcees | All tables and both complete documents match; only escaped titles and line endings are normalized |
| Independent validation oracle | Every Robot Game, Innovation, Robot Design, and GP input; blanks, negative, excessive, fractional, boolean, nonnumeric, formula errors | Browser blocking, missing-award, and warning outcomes agree with Python |
| Saved calculations | Every checked total/rank, missing cache and deliberately incorrect value | Block downloads; identify the column and team |
| Root-cause presentation | One missing input in each score area; two independent blanks; bad input plus other-division stale calculation | One actionable error per input with sheet/cell/team; no rank cascade; preserve independent errors |
| Calculation grouping | Multiple stale saved calculations with valid inputs | One recalculate/save message per workbook; retain detailed mismatches in diagnostic report |
| Positive boundaries | All-zero scores, maximum rubric/GP scores, robot maximum, overridden robot maximum | Accept consistent saved results; zero awards/advancement render without phantom selections |
| Ranking | Minimum ranks, ascending Champion ties, tied awarded Robot Game positions | Preserve numerical semantics; block unresolved awarded ties |
| Configuration schema | INFO/AWARDS absent or wrong type, missing name, nonboolean flags, invalid maximum | Actionable rejection |
| Award definitions | Missing/duplicate IDs, invalid allocations, missing/colliding tags, missing/blank/duplicate labels, shared Robot Game allocations | Reject invalid configurations |
| Workbook selection | None, duplicate files/divisions, missing division, mixed tournaments, mixed legacy/embedded, renamed files, sole configured D2 | Reject inconsistent sets; support identity-based renaming and configured sole divisions |
| Config authority | Reverse file selection, different D2 config, reordered JSON keys | D1 remains authoritative; warn on substantive differences only |
| Legacy compatibility | JSON fallback, absent JSON, filename mismatch, custom template | Support standard fallback; reject mismatches and custom templates explicitly |
| Named tables | Each required table removed, moved to wrong sheet, duplicate headers, each required column removed | Block with contextual error |
| Team identity | Missing, invalid, duplicate, cross-division duplicate, reordered table rows | Reject inconsistent identities; align valid rows by team number |
| Awards / advancement | Unknown/duplicate awards, missing winner, wrong counts, invalid selection, alternate warnings | Block hard errors; require deliberate approval for permitted omissions |
| Open XML reader | Truncated/nonworkbook ZIP, malformed XML, wrong config version/marker, absent chunk/identity, invalid chunk count/division | Reject without producing documents |
| Large/malformed input | Oversized file, expanded ZIP limit, excessive table range | Reject before excessive decompression or table allocation |
| Strings / escaping | Shared strings in real workbooks, inline strings in controlled workbook, Unicode and boundary spaces in chunked config, HTML-like names/titles | Preserve text; escape output; do not execute injected markup |
| File input and drag/drop | Actual File/DataTransfer events on production controls | Load and validate correctly |
| Downloads | Click each real download button and inspect captured Blob bytes/name | Match prepared documents and Python filenames |
| Preview | Open/close preview; attempt preview before approval | Use sandboxed srcdoc; show only approved outputs |
| Approval gates | Warning acknowledgment, lowercase yes, exact YES, reselect files | Only explicit current approvals unlock documents; reset on every new selection |
| Reports | Run one case then another; export after error or new selection | Report latest files, current outcome, and approval state; never old fixture results |
| Recovery | Empty/unsupported/corrupt/lock files, bad/multiple JSON, valid selection after failure | Clear stale outputs immediately; allow correction and retry |
| Concurrency | Slow file read overtaken by a newer selection | Newer selection wins; old result cannot replace it |
| Reset | Start over after success | Remove results, previews, reports, approvals, and selected files |
| Refresh | Retained handles return corrected saved bytes, unreadable/moved files, retry, canceled picker, snapshot-only selection | Reopen every handle; clear stale output immediately; recover on retry; explain fallback; reset approvals |
| Offline packaging | Run directly from file URL with DNS blocked | No server or network dependency |

207 of the error cases come from the independent Python validator oracle.
The total count is recorded in each browser report; adding coverage changes it.
The production HTML must contain neither `TEST_DATA` nor any Dunford fixture.

## Manual acceptance before broad distribution

These checks need real devices and user interactions, not simulated events.

1. On Windows Edge and Chrome, double-click a copied `TOAST.html` outside the
   project. Use the native file picker and drag/drop to load Dunford. Download
   both documents and a report. Verify names and destination behavior.
2. Repeat on macOS Safari and Chrome; repeat on Firefox on an available platform.
   Record browser/OS versions and attach reports. Do not mark untested platforms
   as supported merely because a Chromium test passed.
3. Disconnect networking, close the browser, reopen the standalone HTML, select
   the saved OJS files again, and generate both documents. Repeat after copying
   the HTML and fake tournament to another folder.
4. Inspect both preview documents and downloaded files. Check award presentation
   order, single/two divisions, alternates in summary, dual-emcee colors, long
   team names, page breaks, and printing/PDF through the browser print dialog.
5. At 200% zoom and with keyboard only, complete file selection, warning review,
   omitted-award approval, previews, report export, and reset. Check visible
   focus, labels, status announcements, and no horizontal overflow.
6. Use Choose files to select a copy of Dunford in Chrome/Edge. Edit it in Excel,
   recalculate/save, and click Check again without reselecting. Verify that the
   correction is reflected and all prior approvals clear, including when Excel
   replaces the file while saving. Repeat with drag/drop. Test moved/deleted files,
   revoked permissions, and cancellation. On browsers without file handles, check
   that the explanatory fallback opens the selector. Automated refresh tests use
   controlled handles; this real-device check verifies native OS/Excel behavior.
   Do not change other tournament folders.
7. Ask someone unfamiliar with TOAST to generate both documents from the fake
   event without console instructions. Record confusing steps before release.
8. Try a school-managed browser/device if that is part of the intended audience.
   Local HTML and download policy restrictions remain administrator-controlled.

## Failure triage

- For oracle mismatches, inspect the original Python validation outcome and the
  browser's case report; do not change expected results merely to make tests pass.
- For document mismatches, compare full content. Preserve award order, NONE
  placeholders, grammar, and emcee alternation; document intentional changes.
- For a browser error, retain its report/stderr and screenshots. Runner failures
  must remain nonzero even if an older report file exists.
- New bug fixes should gain a regression scenario in the relevant matrix area.

## Final Notes

The automated suite establishes behavior on the tested browser versions and fake
fixtures; it cannot guarantee all Excel producers, operating systems, or managed
device policies. Broad release requires the manual platform/offline/printing
checks above, while MAESTRO and Python TOAST remain available for rollback.
