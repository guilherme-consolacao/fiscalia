# Graph Report - D:\Fontes\pessoal\fiscalia  (2026-10-19)

## Corpus Check
- Corpus is ~27,184 words - fits in a single context window. You may not need a graph.

## Summary
- 596 nodes · 1212 edges · 56 communities (30 shown, 26 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_news.py / test_news_ai.py
- news_analysis.py / backfill_news_analysis.py
- dashboard_weekly_summary.py / dashboard.py
- news.py / news_import_jobs.py
- news_import.py
- index.html / README.md
- app.js
- news_item.py / news_import_job.py
- news_item.py / news_item_follow.py
- tags.py / api.py
- sources.py / dashboard_weekly_summary.py
- dashboard_weekly_summary.py / source_category.py
- news_item_analysis.py
- test_accessibility_templates.py
- test_sources.py
- test_dashboard.py
- test_tags.py
- news_import_progress.js
- news_import_job.py
- test_news.py / test_news_ai.py
- news.js
- dashboard.js
- 0002_seed_source_categories.py
- 0005_seed_default_tags.py
- 0013_seed_default_receita_federal_source.py
- tag.py
- import-progress-bro.svg
- tags.js
- apps.py
- news_extras.py
- manage.py
- asgi.py
- wsgi.py
- 0001_initial.py
- 0003_create_source.py
- 0004_create_tag.py
- 0006_create_news_item.py
- 0007_create_news_item_analysis.py
- 0008_create_news_import_job.py
- 0009_news_import_job_redirect_relevance.py
- 0010_create_dashboard_weekly_summary.py
- 0011_news_import_job_redirect_effective_dates.py
- 0012_create_news_item_follow_and_reminder_notification.py
- 0014_news_import_job_redirect_sort.py
- 0015_source_tags_and_analysis_score_boost.py

## God Nodes (most connected - your core abstractions)
1. `NewsViewTests` - 36 edges
2. `NewsAnalysisTests` - 32 edges
3. `DummyResponse` - 30 edges
4. `NewsItemAnalysis` - 28 edges
5. `NewsItem` - 24 edges
6. `DummyJsonResponse` - 24 edges
7. `build_feed()` - 18 edges
8. `_clean_text()` - 17 edges
9. `_generate_weekly_summary_with_llm()` - 15 edges
10. `NewsImportJob` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Asynchronous weekly summary status display` --conceptually_related_to--> `Optional OpenAI analysis pipeline`  [INFERRED]
  templates/pages/dashboard/index.html → README.md
- `RSS import followed by optional AI analysis` --conceptually_related_to--> `Optional OpenAI analysis pipeline`  [INFERRED]
  templates/pages/news/import_progress.html → README.md
- `Stored AI summary, impact, keywords, effective date and score explanation` --conceptually_related_to--> `Optional OpenAI analysis pipeline`  [INFERRED]
  templates/pages/news/index.html → README.md
- `DashboardViewTests` --uses--> `DummyResponse`  [INFERRED]
  feeds/tests/test_dashboard.py → feeds/tests/test_news.py
- `Django environment configuration` --references--> `Pinned Python and Django runtime dependencies`  [EXTRACTED]
  README.md → requirements.txt

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **RSS import, optional analysis and source-specific tag scoring feed fiscal insights** — readme_optional_ai_pipeline, templates_pages_news_import_progress_two_stage_pipeline, templates_pages_sources_partials_create_modal_source_tag_scoring, templates_pages_news_index_analysis_display, templates_pages_dashboard_index_dashboard [INFERRED 0.95]
- **Create, edit and delete dialogs share CSRF-protected accessible mutation forms** — templates_pages_sources_partials_create_modal_create_source, templates_pages_sources_partials_edit_modal_edit_source, templates_pages_sources_partials_delete_modal_delete_source, templates_pages_tags_partials_create_modal_create_tag, templates_pages_tags_partials_edit_modal_edit_tag, templates_pages_tags_partials_delete_modal_delete_tag, templates_pages_sources_partials_create_modal_csrf_protected_forms, templates_pages_tags_partials_create_modal_accessible_dialog_pattern [EXTRACTED 1.00]

## Communities (56 total, 26 thin omitted)

### Community 0 - "test_news.py / test_news_ai.py"
Cohesion: 0.05
Nodes (25): NewsAnalysis429Tests, override_settings, NewsAnalysisTests, NewsAnalysisProviderHttpErrorTests, override_settings, override_settings, TestCase, NewsAnalysisResponseParsingTests (+17 more)

### Community 1 - "news_analysis.py / backfill_news_analysis.py"
Cohesion: 0.07
Nodes (53): BaseCommand, Command, _generate_weekly_summary_with_llm(), _analysis_is_current(), _build_input_hash(), build_news_analysis_service(), _build_openai_payload(), _build_openai_quota_message() (+45 more)

### Community 2 - "dashboard_weekly_summary.py / dashboard.py"
Cohesion: 0.08
Nodes (38): _build_assistance_description(), _build_network_status(), _build_sources_description(), _build_weekly_summary_description(), _get_current_week_summary(), sidebar_context(), _truncate_text(), _build_news_url() (+30 more)

### Community 3 - "news.py / news_import_jobs.py"
Cohesion: 0.08
Nodes (32): build_news_import_feedback(), _build_completion_message(), _mark_job_failed(), NewsImportJobReporter, run_news_import_job(), start_news_import_job(), NewsImportResult, _build_reminder_payload() (+24 more)

### Community 4 - "news_import.py"
Cohesion: 0.14
Nodes (35): _build_dedupe_key(), _build_news_payload(), _clean_summary(), _clean_text(), _clean_url(), _cleanup_structural_items(), _describe_feed_fetch_error(), _describe_unimportable_feed() (+27 more)

### Community 5 - "index.html / README.md"
Cohesion: 0.12
Nodes (32): Django environment configuration, Fiscalia RSS tax information portal, English internal identifiers and Portuguese user interface, Optional OpenAI analysis pipeline, Page and domain module organization, Django checks and regression tests, Pinned Python and Django runtime dependencies, Skip link and accessible responsive navigation (+24 more)

### Community 6 - "app.js"
Cohesion: 0.16
Nodes (23): buildEffectiveReminderCard(), closeIconMarkup(), closeSidebar(), convertMessagesToToasts(), dismissEffectiveReminder(), focusModal(), getCookie(), getFocusableElements() (+15 more)

### Community 7 - "news_item.py / news_import_job.py"
Cohesion: 0.12
Nodes (13): display, NewsImportJobAdmin, register, NewsItemAnalysisAdmin, register, NewsItemAdmin, register, register (+5 more)

### Community 8 - "news_item.py / news_item_follow.py"
Cohesion: 0.16
Nodes (8): Meta, NewsItemFollow, Meta, NewsItem, Meta, NewsItemReminderNotification, Meta, Source

### Community 9 - "tags.py / api.py"
Cohesion: 0.21
Nodes (12): csrf_exempt, exemplo_post(), create_tag(), delete_tag(), _is_valid_color(), _is_valid_tag_name(), require_POST, _save_tag() (+4 more)

### Community 10 - "sources.py / dashboard_weekly_summary.py"
Cohesion: 0.31
Nodes (13): invalidate_current_week_summary(), create_source(), delete_source(), _get_source_category(), _get_source_tags(), _parse_tag_ids(), require_POST, _save_source() (+5 more)

### Community 11 - "dashboard_weekly_summary.py / source_category.py"
Cohesion: 0.22
Nodes (4): DashboardWeeklySummary, Meta, Meta, SourceCategory

### Community 13 - "test_accessibility_templates.py"
Cohesion: 0.21
Nodes (5): BaseAccessibilityTemplateTests, NewsAccessibilityTemplateTests, TestCase, SourceAccessibilityTemplateTests, TagAccessibilityTemplateTests

### Community 15 - "test_dashboard.py"
Cohesion: 0.22
Nodes (3): DashboardViewTests, override_settings, TestCase

### Community 17 - "news_import_progress.js"
Cohesion: 0.50
Nodes (7): pollStatus(), renderPayload(), scheduleRedirect(), setCardState(), setChip(), setText(), setWidth()

### Community 20 - "news.js"
Cohesion: 0.47
Nodes (3): getCookie(), renderFollowButton(), setupFollowForms()

### Community 21 - "dashboard.js"
Cohesion: 0.70
Nodes (4): renderSummary(), setText(), startPolling(), toggleVisibility()

### Community 26 - "import-progress-bro.svg"
Cohesion: 0.50
Nodes (4): Completion status shown by checkmarks, Import progress illustration, Record import represented by a left-pointing arrow and document panels, User represented by a person

### Community 27 - "tags.js"
Cohesion: 1.00
Nodes (3): bindColorPicker(), selectColor(), updatePickerState()

## Ambiguous Edges - Review These
- `Authorization rules absent from visible templates` → `Single and bulk read state with effective-date follow actions`  [AMBIGUOUS]
  templates/base.html · relation: conceptually_related_to
- `Authorization rules absent from visible templates` → `RSS source management page`  [AMBIGUOUS]
  templates/base.html · relation: conceptually_related_to
- `Authorization rules absent from visible templates` → `Tag management page`  [AMBIGUOUS]
  templates/base.html · relation: conceptually_related_to

## Knowledge Gaps
- **31 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Authorization rules absent from visible templates` and `Single and bulk read state with effective-date follow actions`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Authorization rules absent from visible templates` and `RSS source management page`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Authorization rules absent from visible templates` and `Tag management page`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NewsItemAnalysis` connect `news_item_analysis.py` to `news_analysis.py / backfill_news_analysis.py`, `dashboard_weekly_summary.py / dashboard.py`, `news.py / news_import_jobs.py`, `news_item.py / news_import_job.py`, `news_item.py / news_item_follow.py`, `dashboard_weekly_summary.py / source_category.py`, `test_news.py / test_news_ai.py`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `NewsItem` connect `news_item.py / news_item_follow.py` to `news_analysis.py / backfill_news_analysis.py`, `dashboard_weekly_summary.py / dashboard.py`, `news.py / news_import_jobs.py`, `news_import.py`, `news_item.py / news_import_job.py`, `dashboard_weekly_summary.py / source_category.py`, `test_accessibility_templates.py`, `test_news.py / test_news_ai.py`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `NewsViewTests` connect `test_news.py / test_news_ai.py` to `test_news.py / test_news_ai.py`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `patch` (e.g. with `.test_refresh_news_shows_quota_message_when_openai_reports_insufficient_quota()` and `.test_backfill_news_analysis_processes_pending_news_items()`) actually correct?**
  _`patch` has 30 INFERRED edges - model-reasoned connections that need verification._

Semantic extraction executed by the current Codex session. Per-agent token usage was not exposed; zeros indicate unavailable telemetry, not zero cost.
