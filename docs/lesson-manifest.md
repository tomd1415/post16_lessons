# Lesson manifest format

File: `web/lessons/manifest.json`

Purpose: Provide a single source of truth for the course catalogue, lesson metadata, and activity mappings. Hubs render directly from this file.

## Top-level shape
- `course`
  - `id`, `title`, `shortTitle`, `version`, `lessonsTotal`
- `linksRegistry`
  - `items` (handbook link registry entries)
- `lessons` (array of lesson objects)

## Lesson object
- `id` (string, unique)
- `number` (integer)
- `title` (string)
- `summary` (string)
- `status` (`ready`, `draft`, or `placeholder`)
- `studentPath` (string, URL path to student hub)
- `teacherPath` (string, URL path to teacher hub)
- `timings` (string)
- `objectives` (array of `{id, text}`)
- `resources` (array of strings)
- `teacherResources` (array of `{title, path}`)
- `activities` (array of activity objects)

## Activity object
- `id` (string)
- `title` (string)
- `path` (string, URL path to activity page)
- `objectiveIds` (array of objective ids)
- `expectedEvidence` (string)
- `rubricHook` (string or null; reserved for Phase 4+)

## Notes
- Lesson 1 is populated with real metadata and activity mappings.
- Lessons 2-15 are populated from the teacher handbook; lesson shells remain placeholders until packs are built.
- The catalogue UI uses the manifest directly; there is no additional build step.

## Link registry item
Fields in `linksRegistry.items`:
- `id` (string, unique)
- `lessonId` (string)
- `title` (string)
- `url` (string)
- `section` (`additional` or `exercise`)
- `status` (string, optional; set by link checker)
- `lastChecked` (ISO timestamp, optional)
- `replacementUrl` (string, optional)
- `localPath` (string, optional)

Link overrides are stored in `data/link-overrides.json` and exposed via `GET /api/teacher/links`.
Use `scripts/link_registry_check.py` to refresh `status` + `lastChecked` in the manifest.
