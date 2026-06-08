# CareersDNA Analytics Playbook

This file defines what to read in GA4/Search Console and how to translate it into product changes.

## Core Funnel

Use GA4 Explore > Funnel exploration.

1. `view_home`, `view_test_landing`, `view_career_detail`, or `view_careers_index`
2. `click_start_from_home`, `click_start_from_landing`, `click_start_from_career`, or `click_start_from_careers_index`
3. `view_survey_section` where `section_index = 0`
4. `complete_section`
5. `view_result`
6. `copy_share_url`, `native_share`, `download_report`, or `result_career_detail`

## What To Watch

- Landing page conversion: `click_start_from_landing / view_test_landing`
- Career page conversion: `click_start_from_career / view_career_detail`
- Survey dropoff by section: compare `view_survey_section` to `complete_section` by `section_key`
- Content engagement: `scroll_depth` at 50/75/90 and `engaged_time` at 45/90 seconds
- Result value: `copy_share_url`, `download_report`, `result_career_detail`
- SEO demand: Search Console queries and pages with rising impressions
- Money pages: AdSense page RPM by URL path

## Decision Rules

- If a test landing gets impressions but low start clicks, rewrite the first screen and CTA.
- If a career page has high 75% scroll depth but low start clicks, add a stronger mid-page CTA.
- If a survey section has high exits, reduce text, split the section, or make progress clearer.
- If result page has low career-detail clicks, improve top-match cards and explain why each match matters.
- If a topic has high Search Console impressions, create adjacent pages for related careers and tests.

## Event Names

- `page_view_custom`
- `view_home`
- `view_test_landing`
- `view_career_detail`
- `view_careers_index`
- `view_survey_section`
- `complete_section`
- `survey_section_exit`
- `survey_back`
- `view_result`
- `scroll_depth`
- `engaged_time`
- `click_start_from_home`
- `click_start_from_landing`
- `click_start_from_career`
- `click_start_from_careers_index`
- `click_home_test`
- `click_home_career`
- `click_landing_career`
- `click_related_test`
- `click_related_career`
- `click_careers_index_item`
- `copy_share_url`
- `native_share`
- `download_report`
- `result_career_detail`

## Weekly Review

Export or screenshot:

- GA4 Pages and screens
- GA4 Events
- GA4 Funnel exploration
- Search Console Performance: Queries and Pages
- AdSense Reports: Pages, Countries, Platforms

Prioritize changes where traffic, engagement, and revenue potential overlap.
