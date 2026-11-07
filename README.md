# ABL League Events Calendar

A free, GitHub Pages-hosted iCalendar subscription feed. `events.csv` is the single source of truth; GitHub Actions rebuilds and publishes `site/abl-events.ics` whenever the CSV or generator changes.

## What it publishes

League administration events such as meetings, draft dates, roster deadlines, rule-change deadlines, awards voting, and other milestones. This is **not** intended as a game schedule.

## 1. Create the GitHub repository

Create a new **public** repository (for example, `abl-calendar`) under the GitHub account or organization that should own the league calendar. Upload all files from this project, preserving the directory structure, and use `main` as the default branch.

A public repository is required for a publicly accessible GitHub Pages subscription feed on the free GitHub plan.

## 2. Enable GitHub Pages

In the repository:

1. Open **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. Save.

The included workflow deploys the `site/` directory to Pages. No custom domain is required.

## 3. Add events

Edit `events.csv` in GitHub's web interface (or locally and commit the change). Keep the header row exactly as supplied.

| Column | Required | Meaning |
|---|---|---|
| `id` | Yes | Permanent unique identifier; use letters, numbers, `.`, `_`, `-` only. Never change an ID after publishing an event. |
| `title` | Yes | Event title shown in calendars. |
| `description` | No | Details; do not put confidential information here. |
| `start` | Yes | Start date/time. |
| `end` | Yes | End date/time. For all-day events, this is the **exclusive** end date (the day after the event). |
| `all_day` | Yes | `TRUE` or `FALSE`. |
| `timezone` | No | IANA timezone for a time without an offset, e.g. `America/Los_Angeles`. Defaults to `America/Los_Angeles`. |
| `location` | No | Venue or meeting URL. |
| `category` | No | E.g. `Meeting`, `Draft`, `Deadline`, `Administration`. |
| `status` | No | `CONFIRMED`, `TENTATIVE`, or `CANCELLED`; defaults to `CONFIRMED`. |
| `recurrence_frequency` | No | Recurrence frequency. Currently only `WEEKLY` is supported. |
| `recurrence_interval` | No | Number of weeks between occurrences for `WEEKLY`; defaults to `1`. Must be a positive integer and requires `recurrence_frequency`. |
| `recurrence_until` | No | Inclusive final date on which an occurrence may start, in `YYYY-MM-DD` format. Required when recurrence is specified. |

### Date/time format

- Timed event: `2027-02-06T10:00` with a `timezone` column, or an ISO timestamp with an explicit offset such as `2027-02-06T10:00:00-08:00`.
- All-day event: `2027-02-20` through `2027-02-21` for a one-day event (end date is exclusive).
- Use 24-hour time.
- For timed events, the generator converts local time to UTC. Calendar apps display it in each subscriber's local timezone.

`events.example.csv` contains examples; copy rows into `events.csv` and replace the sample values.

### Recurring events

- Leave all three recurrence fields blank for a one-time event.
- For a weekly series, set `recurrence_frequency` to `WEEKLY`, set `recurrence_interval` to the number of weeks between occurrences, and set `recurrence_until` to the inclusive date limit.
- The first occurrence is the event's `start` and `end`. The generator expands subsequent occurrences through `recurrence_until`; each occurrence is published as a separate calendar event with a generated ID based on the original ID and occurrence date.
- For recurring timed events, enter local wall-clock times without a UTC offset and set the `timezone`. The generator preserves that local time across daylight-saving changes. Recurring all-day events use calendar dates; their `end` remains exclusive.
- To include a break in a series, split it into two rows: the first row ends with the last occurrence before the break, and the second row starts at the first occurrence after the break. Give the second row a different base `id`. The break itself can be added as a separate one-time event.
- Recurrence exceptions, skipped individual dates, and monthly/yearly recurrence are not currently supported.

Example: a biweekly series starting February 4, with occurrences every two weeks through April 22, uses `WEEKLY`, interval `2`, and `recurrence_until` `2027-04-22`.

### Changing or cancelling events

- **Update:** edit the existing row; keep its `id`. Subscribers' apps should treat it as an update, not a new event.
- **Cancel:** change `status` to `CANCELLED` and retain the row. Do not simply remove a published event if you need subscribers to receive a cancellation.
- **Delete:** remove a row only if it was never published, or if you accept that some calendar apps may retain the old event until manually removed. iCalendar clients vary in how they process deletions from published feeds.

## 4. Share the subscription URL

After the first successful workflow run, the public feed will be:

`https://OWNER.github.io/REPOSITORY/abl-events.ics`

Replace `OWNER` and `REPOSITORY` with the actual GitHub owner and repository name. The landing page is:

`https://OWNER.github.io/REPOSITORY/`

Share the `.ics` URL as the subscription link. Do not use the GitHub `raw.githubusercontent.com` URL; the Pages URL is the stable public feed.

## 5. Updating and troubleshooting

- Every commit that changes `events.csv` triggers a rebuild and Pages deployment.
- You can also run the workflow manually from **Actions → Build and publish ABL calendar → Run workflow**.
- Check the Actions run if a CSV edit does not appear on the public feed.
- Subscribers' calendar apps poll feeds on their own schedules; updates are not necessarily immediate.
- No secrets, API keys, external services, or paid hosting are required.

## Local validation

Requires Python 3.9+ (the workflow uses current Python). Run:

```bash
python scripts/build_calendar.py
```

The generated feed appears at `site/abl-events.ics`.
