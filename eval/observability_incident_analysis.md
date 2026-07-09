# Day 5, Session 3, Exercise 5 — Log Analysis: Two Production Anomalies

Source data: the simulated one-week log summary given in the exercise brief
(Monday-Friday query counts, avg latency, total cost, error counts, plus the
Wednesday/Friday detail breakdowns). Two days deviate from the Mon/Tue/Thu
baseline (~95-110 queries, ~2.1-3.8s avg latency, ~$0.28-0.33/day, 0-3 errors).

## Anomaly 1 — Wednesday: a $4.82 day (16x the baseline)

**Root cause.** 3 of Wednesday's 98 queries had `input_tokens > 15,000` versus
a normal ~1,200 — roughly a 12x jump on just those 3 requests — and those 3
queries alone account for $4.40 of the $4.82 total (~91% of the day's spend
from ~3% of its traffic). Query count and error count are both normal, so
this isn't a pipeline-wide regression; it's 3 individual requests carrying an
abnormally large prompt. Given the chatbot's architecture (retrieval always
returns `top_k=6` short chunks, and history is folded into a summary every 10
turns — see `spec.md` "Memory"), a per-query token count that high is most
consistent with a user pasting a large block of text directly into the chat
input (an essay, a syllabus PDF's text, a whole email thread) rather than
asking a short question — exactly the "worst cost blowout scenario" this same
session's Exercise 3 input-length validator was built to catch.

**Metric that would have caught it.** Cost per query, in real time. Each of
the 3 queries cost roughly $1.47 individually — 14x the per-query cost alert
threshold. A secondary signal, `input_tokens` per query against its own
historical baseline (~1,200), would have flagged it even earlier, before the
request was ever billed.

**Alert threshold.** `cost_per_query > $0.10` (already defined for this
project, `observability.COST_PER_QUERY_ALERT_USD`) — would have fired on all
3 queries individually. A second, more preventive threshold —
`input_tokens > 5,000` (roughly 4x the observed normal ceiling) — checked
*before* the request is sent, not after it's billed, would have blocked the
spend entirely rather than just reporting on it afterward.

**Production fix.** The input-length validator built in Exercise 3
(`observability.validate_input_length`, rejecting anything over 2,000
characters before it reaches retrieval/generation) directly closes this hole
at the UI layer. Two things worth adding on top of what's built here: (1)
enforce the same check at the `pipeline.answer_question()` level, not only in
`pages/0_Chat.py` — so any other caller (the eval scripts, a future API
endpoint) gets the same protection instead of relying on every caller to
remember it; (2) truncate or reject an oversized `history` list defensively
in `pipeline.trim_history`, since a pasted essay could in principle also
arrive as an injected "assistant" turn via history rather than the live
`query` string.

## Anomaly 2 — Friday: 12 RateLimitErrors clustered in one hour, latency 8.5s

**Root cause.** All 12 of Friday's errors are `RateLimitError`, and they're
clustered entirely between 4:00-5:00 PM; average latency outside that window
is 2.4s (normal), meaning the day's inflated 8.5s average is being dragged up
entirely by that one hour, not a day-long slowdown. This is a classic
traffic-burst-vs-rate-limit pattern: query *volume* spiked during that hour
(a likely cause for a college FAQ bot — e.g. many students hitting the site
around the same time, perhaps after a class or a deadline reminder), pushing
the account past its requests-per-minute ceiling with the upstream provider.
The resulting errors and the elevated latency are two symptoms of the same
cause (queueing/backoff behavior around a saturated rate limit), not two
separate problems.

**Metric that would have caught it.** The rolling error rate over the last N
queries (this project already defines
`observability.ERROR_RATE_ALERT_FRACTION = 5%` over the last 20 queries) —
12 errors within one hour's traffic would blow past 5% well before the hour
ended. A second, earlier-warning metric — requests per minute against the
account's known provider rate limit — would catch the *cause* (the traffic
spike) before it turns into errors at all, rather than reacting after the
first failures.

**Alert threshold.** `error_rate > 5%` over the last 20 queries (already
defined here) as the reactive catch, plus a proactive
`requests_per_minute > (provider RPM limit x 0.8)` warning so the team gets
paged on the buildup, not just the failures.

**Production fix.** Add client-side retry with exponential backoff so a
transient `RateLimitError` becomes a slightly slower successful answer for
the user instead of a hard failure; add a request queue/rate limiter sized
just under the provider's actual RPM ceiling so the app self-throttles
instead of the provider rejecting it; and if this traffic pattern recurs
regularly (e.g. every weekday afternoon), that's a signal to request a higher
rate-limit tier from the provider rather than continuing to smooth over a
capacity problem with retries alone.

## Monitoring dashboard sketch

A single "BVRIT Chatbot Health" view, one week at a time:

- **Top row — KPI tiles** (today vs. 7-day average, colored by the
  thresholds above): queries today, avg latency, P95 latency, cost today,
  error rate. A tile turns amber/red the moment its own threshold is
  breached, so both anomalies are visible at a glance without reading a
  single log line.
- **Cost-per-day bar chart**, one bar per day of the week. Wednesday's $4.82
  bar stands out immediately next to five ~$0.30 bars — the anomaly is
  visible from across the room.
- **Latency line chart (P50 and P95), hourly buckets across the week.**
  Friday's 4-5 PM hour shows as a sharp spike against an otherwise flat
  line — the clustering that a daily average alone (8.5s) hides.
- **Error count, hourly buckets, colored by error type.** Same shape as the
  latency chart, confirming the two are the same incident, not a
  coincidence — a `RateLimitError`-colored spike lands in the exact hour as
  the latency spike.
- **Input-token distribution (histogram), refreshed daily.** Wednesday's 3
  outlier queries appear as a handful of bars far to the right of an
  otherwise tight cluster around ~1,200 tokens — this is what would let
  someone *notice* the Wednesday pattern even without the cost figure.

## For the dean (non-technical)

This week, the chatbot had two unusual days. On Wednesday, a small number of
questions were unusually long — likely someone pasting in a large amount of
text rather than asking a short question — and because the chatbot pays a
provider per word processed, those few questions cost as much as the rest of
the entire week combined; we're adding a check that politely asks anyone who
pastes something that long to shorten it to a specific question, which
prevents this automatically going forward. On Friday, during a one-hour
window with unusually high traffic — most likely many students using it at
the same time — the chatbot's external AI provider temporarily refused some
requests because we were asking it to do too much too quickly, similar to a
phone line being busy; a handful of students would have seen a "please try
again" message during that hour. We're adding automatic retries so a busy
moment resolves itself with a short delay instead of an error, and if this
becomes a regular afternoon pattern we'll increase our capacity with the
provider rather than continuing to just absorb it.
