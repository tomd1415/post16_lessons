# Lesson manifest format

File: `web/lessons/manifest.json`

Purpose: Provide a single source of truth for the course catalogue, lesson metadata, and activity mappings. Hubs render directly from this file.

## Top-level shape
- `course`
  - `id`, `title`, `shortTitle`, `version`, `lessonsTotal`
- `linksRegistry`
  - `items` (reserved for Phase 5 link health checks and replacements)
- `lessons` (array of lesson objects)

## Lesson object
- `id` (string, unique)
- `number` (integer)
- `title` (string)
- `summary` (string)
- `status` (`ready` or `placeholder`)
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
- Lessons 2-8 are placeholders (empty activities/objectives) until Phase 5.
- The catalogue UI uses the manifest directly; there is no additional build step.
