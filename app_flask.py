import os
import sys
import json
import base64
import hashlib
import sqlite3
import tempfile
from datetime import datetime

from flask import Flask, render_template, request, session, redirect, url_for, make_response, jsonify
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.i18n import t, tq, tc, tcat, LANG_CONFIG, UI
try:
    from data.career_descriptions import CAREER_DESC_EN
except ImportError:
    CAREER_DESC_EN = {}

try:
    from data.career_global import CAREER_GLOBAL_DATA
except ImportError:
    CAREER_GLOBAL_DATA = {}

try:
    from data.career_reviews import CAREER_REVIEWS
except ImportError:
    CAREER_REVIEWS = {}

try:
    from engine.interpreter import generate_insight
except ImportError:
    generate_insight = None
from data.questions import (
    get_assessment_plan, get_age_group,
    HOLLAND_LABELS, MI_LABELS, BIG5_LABELS, VALUES_LABELS, ANCHOR_LABELS,
)
from engine.scorer import score_all_modules
from engine.matcher import rank_careers, get_career_fit_summary
from data.careers import CAREERS_DB, get_careers_by_category

# ────────────────────────────────────────────────
# Flask app setup
# ────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "jinro-secret-key-change-in-prod")
DEFAULT_LANG = "en"
APP_URL = os.environ.get("APP_URL", "https://jinro-assessment.onrender.com").rstrip("/")
DEFAULT_ADSENSE_CLIENT = "ca-pub-6018524927950587"
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "9e7a7feff4e24bb7aaefbc5fb60d6d3d")
ANALYTICS_DB = os.environ.get(
    "ANALYTICS_DB",
    os.path.join(tempfile.gettempdir(), "careersdna", "analytics.sqlite3"),
)

SEO_TEST_PAGES = {
    "high-school-career-test": {
        "title": "High School Career Test",
        "headline": "Career test for high school students",
        "description": "Explore career directions based on interests, strengths, personality, and work values. Built for students who want practical next steps.",
        "age_hint": "13-18",
        "keywords": ["high school career test", "student career quiz", "career aptitude test"],
    },
    "job-aptitude-test": {
        "title": "Job Aptitude Test",
        "headline": "Find career paths that fit how you think and work",
        "description": "A multi-theory assessment that compares your answers with 174 career profiles and explains why each path may fit.",
        "age_hint": "19-29",
        "keywords": ["job aptitude test", "career match test", "work personality test"],
    },
    "career-change-test": {
        "title": "Career Change Test",
        "headline": "Career change test for adults",
        "description": "Use your interests, values, personality, and career anchors to identify realistic career-change options.",
        "age_hint": "30+",
        "keywords": ["career change test", "career switch quiz", "adult career assessment"],
    },
    "middle-school-career-test": {
        "title": "Middle School Career Test",
        "headline": "A simple career test for middle school students",
        "description": "Start with interests and strengths, then compare possible career areas without forcing one final answer.",
        "age_hint": "13-15",
        "keywords": ["middle school career test", "student aptitude quiz"],
    },
    "college-career-test": {
        "title": "College Career Test",
        "headline": "Career test for college students choosing a direction",
        "description": "Compare careers by interests, personality, values, and practical preparation paths before choosing internships or majors.",
        "age_hint": "19-29",
        "keywords": ["college career test", "major career test", "graduate career quiz"],
    },
    "personality-career-test": {
        "title": "Personality Career Test",
        "headline": "Match career options with your personality and work style",
        "description": "Use personality signals alongside interests and values so the result is not just about what sounds fun.",
        "age_hint": "All",
        "keywords": ["personality career test", "work style test"],
    },
    "career-values-test": {
        "title": "Career Values Test",
        "headline": "Find careers that fit what you value at work",
        "description": "Compare income, stability, autonomy, creativity, social contribution, and growth as part of your career decision.",
        "age_hint": "16+",
        "keywords": ["career values test", "work values quiz"],
    },
    "developer-aptitude-test": {
        "title": "Developer Aptitude Test",
        "headline": "See whether software development is worth exploring",
        "description": "Compare developer work with your problem-solving style, patience for detail, learning habits, and related career alternatives.",
        "age_hint": "16+",
        "keywords": ["developer aptitude test", "software engineer career test"],
    },
    "designer-aptitude-test": {
        "title": "Designer Aptitude Test",
        "headline": "Explore design careers that match your strengths",
        "description": "Look beyond creativity and compare design careers by spatial thinking, empathy, communication, and work values.",
        "age_hint": "16+",
        "keywords": ["designer aptitude test", "design career quiz"],
    },
    "nurse-aptitude-test": {
        "title": "Nurse Aptitude Test",
        "headline": "Check whether nursing is a realistic career option",
        "description": "Explore fit signals for nursing, including social motivation, detail orientation, stress tolerance, and related healthcare paths.",
        "age_hint": "16+",
        "keywords": ["nurse aptitude test", "nursing career test"],
    },
    "teacher-aptitude-test": {
        "title": "Teacher Aptitude Test",
        "headline": "Explore whether teaching fits your strengths",
        "description": "Compare teaching with your communication style, patience, social motivation, structure, and long-term work values.",
        "age_hint": "16+",
        "keywords": ["teacher aptitude test", "teaching career quiz"],
    },
    "business-career-test": {
        "title": "Business Career Test",
        "headline": "Find business careers that match your work style",
        "description": "Compare marketing, finance, management, entrepreneurship, and operations paths by strengths and values.",
        "age_hint": "16+",
        "keywords": ["business career test", "business aptitude quiz"],
    },
    "creative-career-test": {
        "title": "Creative Career Test",
        "headline": "Explore creative careers without guessing",
        "description": "Compare creative careers by expression, independence, collaboration, income expectations, and practical alternatives.",
        "age_hint": "16+",
        "keywords": ["creative career test", "arts career quiz"],
    },
    "stem-career-test": {
        "title": "STEM Career Test",
        "headline": "Explore science, technology, engineering, and math careers",
        "description": "Compare analytical and technical career paths by interests, strengths, values, and preparation difficulty.",
        "age_hint": "13+",
        "keywords": ["STEM career test", "science career quiz"],
    },
    "healthcare-career-test": {
        "title": "Healthcare Career Test",
        "headline": "Compare healthcare careers that may fit you",
        "description": "Explore healthcare careers by people skills, detail orientation, science interest, stress tolerance, and education path.",
        "age_hint": "16+",
        "keywords": ["healthcare career test", "medical career quiz"],
    },
    "remote-work-career-test": {
        "title": "Remote Work Career Test",
        "headline": "Find careers that may fit remote or flexible work",
        "description": "Compare autonomy, communication, focus, and digital work patterns before choosing remote-friendly paths.",
        "age_hint": "19+",
        "keywords": ["remote work career test", "work from home career quiz"],
    },
    "burnout-career-test": {
        "title": "Burnout Career Test",
        "headline": "Career reflection test for burnout or career confusion",
        "description": "Use a calmer framework to compare work values, energy patterns, and career alternatives when your current path feels unclear.",
        "age_hint": "19+",
        "keywords": ["burnout career test", "career confusion test"],
    },
}

SEO_TEST_DETAILS = {
    "high-school-career-test": {
        "primary_keyword": "career test for high school students",
        "search_title": "Free Career Test for High School Students",
        "intent": "Students can compare possible career directions before choosing classes, clubs, majors, or early projects.",
        "best_for": ["Students choosing school subjects", "Families discussing future majors", "Teens who want realistic options"],
        "compare": ["College Career Test", "STEM Career Test", "Creative Career Test"],
    },
    "job-aptitude-test": {
        "primary_keyword": "job aptitude test",
        "search_title": "Free Job Aptitude Test",
        "intent": "Use this job aptitude test to compare careers by interests, strengths, work style, and values instead of choosing from a generic list.",
        "best_for": ["First job decisions", "People comparing several industries", "Users who want a practical career match"],
        "compare": ["Career Change Test", "Personality Career Test", "Career Values Test"],
    },
    "career-change-test": {
        "primary_keyword": "career change test",
        "search_title": "Free Career Change Test",
        "intent": "Adults can compare new career directions while accounting for work values, transferable strengths, and burnout risk.",
        "best_for": ["Career switch planning", "Burnout reflection", "Adults comparing realistic next steps"],
        "compare": ["Burnout Career Test", "Remote Work Career Test", "Job Aptitude Test"],
    },
    "middle-school-career-test": {
        "primary_keyword": "career test for middle school students",
        "search_title": "Free Career Test for Middle School Students",
        "intent": "Younger students can explore broad career areas without forcing one final job choice too early.",
        "best_for": ["Early career exploration", "School counseling activities", "Students who need simple next steps"],
        "compare": ["High School Career Test", "Creative Career Test", "STEM Career Test"],
    },
    "college-career-test": {
        "primary_keyword": "career test for college students",
        "search_title": "Free Career Test for College Students",
        "intent": "College students can compare majors, internships, and entry-level roles with a career fit framework.",
        "best_for": ["Major decisions", "Internship planning", "Graduation and first-job choices"],
        "compare": ["Job Aptitude Test", "Career Values Test", "Developer Aptitude Test"],
    },
    "personality-career-test": {
        "primary_keyword": "personality career test",
        "search_title": "Free Personality Career Test",
        "intent": "Compare career paths using personality signals alongside interests and values, so the result is not based on personality alone.",
        "best_for": ["Work style comparison", "Introvert or extrovert fit questions", "People who want sustainable work environments"],
        "compare": ["Career Values Test", "Job Aptitude Test", "Remote Work Career Test"],
    },
    "career-values-test": {
        "primary_keyword": "career values test",
        "search_title": "Free Career Values Test",
        "intent": "Clarify whether income, autonomy, stability, creativity, growth, or contribution should guide your career shortlist.",
        "best_for": ["Choosing between good options", "Work-life fit decisions", "People comparing tradeoffs"],
        "compare": ["Personality Career Test", "Career Change Test", "Job Aptitude Test"],
    },
    "developer-aptitude-test": {
        "primary_keyword": "software developer career test",
        "search_title": "Software Developer Career Test",
        "intent": "Check whether coding and software development are worth exploring by comparing problem-solving style, patience, learning habits, and alternatives.",
        "best_for": ["Coding beginners", "Students considering computer science", "Career changers comparing tech roles"],
        "compare": ["STEM Career Test", "Job Aptitude Test", "Remote Work Career Test"],
    },
    "designer-aptitude-test": {
        "primary_keyword": "designer aptitude test",
        "search_title": "Free Designer Aptitude Test",
        "intent": "Compare design careers using creativity, empathy, visual thinking, communication, and practical preparation signals.",
        "best_for": ["Students considering design", "Portfolio planning", "Creative career comparison"],
        "compare": ["Creative Career Test", "Personality Career Test", "Career Values Test"],
    },
    "nurse-aptitude-test": {
        "primary_keyword": "nursing career aptitude test",
        "search_title": "Nursing Career Aptitude Test",
        "intent": "Explore nursing fit using people skills, stress tolerance, detail orientation, science interest, and healthcare alternatives.",
        "best_for": ["Students considering nursing", "Healthcare career comparison", "People checking service-oriented work fit"],
        "compare": ["Healthcare Career Test", "Career Values Test", "Job Aptitude Test"],
    },
}

SEO_GUIDE_PAGES = {
    "what-career-is-right-for-me": {
        "title": "What Career Is Right for Me?",
        "headline": "What career is right for me?",
        "description": "A practical way to narrow career options using interests, strengths, personality, values, and small real-world experiments.",
        "keyword": "what career is right for me",
        "intro": "If you are asking what career is right for me, the useful answer is rarely one job title. A better answer is a shortlist of careers that match how you like to work, what you can build skill in, and what tradeoffs you can accept.",
        "sections": [
            ("Start with work patterns, not job titles", "List the activities that give you energy, the tasks you avoid, the subjects you learn quickly, and the environments where you can stay consistent."),
            ("Compare values early", "A career can look attractive but fail because the daily tradeoffs are wrong. Compare income, autonomy, stability, creativity, growth, and social contribution before committing."),
            ("Use a test as a sorting tool", "A career test should help you compare paths, not declare a final identity. Read the reasons behind the result and review related careers with similar work styles."),
        ],
        "related_tests": ["job-aptitude-test", "personality-career-test", "career-values-test"],
        "related_careers": ["software_dev", "data_scientist", "nurse", "secondary_teacher", "financial_analyst", "ux_designer"],
    },
    "best-careers-for-introverts": {
        "title": "Best Careers for Introverts",
        "headline": "Best careers for introverts to explore",
        "description": "Compare introvert-friendly career paths by focus time, collaboration style, autonomy, communication load, and growth.",
        "keyword": "best careers for introverts",
        "intro": "The best careers for introverts are not always isolated jobs. Many introverts do well in roles with deep focus, clear expectations, thoughtful communication, and enough control over energy-draining interaction.",
        "sections": [
            ("Look for focus and predictable communication", "Roles with project-based work, written communication, research, analysis, design, or technical problem solving can fit many introverted work styles."),
            ("Avoid using introvert as the only filter", "Personality matters, but values, skill growth, income needs, and stress tolerance matter too. Compare the whole career profile."),
            ("Test the environment", "Before choosing a path, ask people in the field how meetings, deadlines, collaboration, and customer contact actually work day to day."),
        ],
        "related_tests": ["personality-career-test", "remote-work-career-test", "job-aptitude-test"],
        "related_careers": ["software_dev", "data_scientist", "writer", "accountant", "biotech_researcher", "ux_designer"],
    },
    "career-test-for-students": {
        "title": "Career Test for Students",
        "headline": "Career test for students choosing a direction",
        "description": "A student-focused guide to using career tests before choosing subjects, majors, clubs, internships, or projects.",
        "keyword": "career test for students",
        "intro": "A career test for students should keep options open while making the next step clearer. The goal is to connect interests and strengths with courses, projects, and careers worth exploring.",
        "sections": [
            ("Do not force one final answer too early", "Students change quickly as they meet new subjects and experiences. A useful result gives several directions to compare."),
            ("Connect careers to school choices", "Use the result to choose classes, clubs, projects, reading topics, internships, or people to interview."),
            ("Review careers by preparation path", "Some careers require licensing or long education. Others can be tested through small projects or entry-level experience."),
        ],
        "related_tests": ["middle-school-career-test", "high-school-career-test", "college-career-test"],
        "related_careers": ["software_dev", "doctor", "secondary_teacher", "graphic_designer", "mechanical_engineer", "financial_analyst"],
    },
    "free-career-aptitude-test": {
        "title": "Free Career Aptitude Test",
        "headline": "Free career aptitude test: how to use the result",
        "description": "Learn what a career aptitude test can and cannot tell you, and how to turn the result into useful next steps.",
        "keyword": "free career aptitude test",
        "intro": "A free career aptitude test is most useful when it compares multiple signals: interests, strengths, personality, values, and practical career data. It should help you decide what to research next.",
        "sections": [
            ("Aptitude is broader than talent", "Career aptitude includes learning speed, motivation, work habits, stress fit, values, and the kind of problems you want to solve."),
            ("The score is a starting point", "High scores should lead to research, not automatic decisions. Compare the daily work, education path, and alternatives."),
            ("Use the result for experiments", "Pick one small test: a course, portfolio task, informational interview, shadowing opportunity, or volunteer experience."),
        ],
        "related_tests": ["job-aptitude-test", "career-values-test", "personality-career-test"],
        "related_careers": ["software_dev", "nurse", "marketer", "counselor", "architect", "data_analyst"],
    },
    "career-change-ideas": {
        "title": "Career Change Ideas",
        "headline": "Career change ideas when your current path does not fit",
        "description": "A practical guide for adults comparing career change options without ignoring income, stability, skills, and burnout.",
        "keyword": "career change ideas",
        "intro": "Career change ideas are only useful if they fit your constraints. The right shortlist should consider transferable skills, income needs, energy, learning time, and the type of work you want to repeat.",
        "sections": [
            ("Separate field change from role change", "Sometimes the issue is not the industry, but the daily tasks, manager style, workload, or growth path."),
            ("Map transferable skills", "Communication, analysis, operations, teaching, sales, design, writing, and technical skills can move across many fields."),
            ("Protect against fantasy careers", "Research salary, entry difficulty, licensing, portfolio requirements, and the first realistic job in the new path."),
        ],
        "related_tests": ["career-change-test", "burnout-career-test", "remote-work-career-test"],
        "related_careers": ["product_manager", "data_analyst", "technical_writer", "corporate_trainer", "business_consultant", "ux_ui_designer"],
    },
    "high-paying-careers-that-fit-your-personality": {
        "title": "High Paying Careers That Fit Your Personality",
        "headline": "High paying careers that may fit your personality",
        "description": "Compare higher-income career paths without ignoring personality fit, work values, preparation difficulty, and stress.",
        "keyword": "high paying careers that fit your personality",
        "intro": "High paying careers are easier to sustain when the work style fits you. Income matters, but so do stress tolerance, detail orientation, social energy, independence, and long-term learning.",
        "sections": [
            ("Income is only one fit signal", "A strong career choice balances earning potential with daily work, preparation time, and the kind of pressure you can handle."),
            ("Compare paths by personality demands", "Some roles reward persuasion and ambiguity. Others reward deep focus, precision, persistence, or structured execution."),
            ("Check the preparation path", "Many high-paying careers require years of education, credentials, portfolio proof, or specialized experience."),
        ],
        "related_tests": ["personality-career-test", "career-values-test", "business-career-test"],
        "related_careers": ["software_dev", "doctor", "lawyer", "financial_analyst", "ai_engineer", "investment_banker"],
    },
}

DAILY_TOOLS = {
    "word-counter": {
        "title": "Word Counter",
        "headline": "Word counter and character counter",
        "description": "Count words, characters, sentences, paragraphs, and reading time for essays, posts, resumes, and emails.",
        "keyword": "word counter",
        "type": "word_counter",
    },
    "random-picker": {
        "title": "Random Picker",
        "headline": "Random picker for names, tasks, and choices",
        "description": "Paste a list and pick a random item. Useful for teams, classrooms, chores, giveaways, and daily decisions.",
        "keyword": "random picker",
        "type": "random_picker",
    },
    "pomodoro-timer": {
        "title": "Pomodoro Timer",
        "headline": "Simple Pomodoro timer for focus sessions",
        "description": "Run repeatable 25-minute focus sessions with short breaks. Designed for studying, writing, and deep work.",
        "keyword": "pomodoro timer",
        "type": "pomodoro",
    },
    "habit-tracker": {
        "title": "Daily Habit Tracker",
        "headline": "Daily habit tracker",
        "description": "Track a few habits locally in your browser and reset each day. No account required.",
        "keyword": "daily habit tracker",
        "type": "habit_tracker",
    },
    "decision-wheel": {
        "title": "Decision Wheel",
        "headline": "Decision wheel for quick choices",
        "description": "Add options and spin a simple decision wheel when you need a fast, low-stakes choice.",
        "keyword": "decision wheel",
        "type": "decision_wheel",
    },
    "case-converter": {
        "title": "Case Converter",
        "headline": "Case converter for text",
        "description": "Convert text to uppercase, lowercase, title case, sentence case, slug case, and snake case.",
        "keyword": "case converter",
        "type": "case_converter",
    },
    "password-generator": {
        "title": "Password Generator",
        "headline": "Password generator",
        "description": "Generate a random password with adjustable length, numbers, symbols, and mixed case.",
        "keyword": "password generator",
        "type": "password_generator",
    },
    "percentage-calculator": {
        "title": "Percentage Calculator",
        "headline": "Percentage calculator",
        "description": "Calculate percentages, percentage change, and what percent one number is of another.",
        "keyword": "percentage calculator",
        "type": "percentage_calculator",
    },
    "age-calculator": {
        "title": "Age Calculator",
        "headline": "Age calculator",
        "description": "Calculate age in years, months, and days from a date of birth.",
        "keyword": "age calculator",
        "type": "age_calculator",
    },
    "time-calculator": {
        "title": "Time Calculator",
        "headline": "Time calculator",
        "description": "Add minutes and hours to a start time, or calculate the duration between two times.",
        "keyword": "time calculator",
        "type": "time_calculator",
    },
    "tip-calculator": {
        "title": "Tip Calculator",
        "headline": "Tip calculator",
        "description": "Calculate tip, total bill, and split amount per person.",
        "keyword": "tip calculator",
        "type": "tip_calculator",
    },
    "unit-converter": {
        "title": "Unit Converter",
        "headline": "Unit converter",
        "description": "Convert common length and weight units including miles, kilometers, pounds, and kilograms.",
        "keyword": "unit converter",
        "type": "unit_converter",
    },
    "text-repeater": {
        "title": "Text Repeater",
        "headline": "Text repeater",
        "description": "Repeat text a set number of times with optional line breaks or spaces.",
        "keyword": "text repeater",
        "type": "text_repeater",
    },
    "pdf-merge": {
        "title": "PDF Merge",
        "headline": "Merge PDF files online",
        "description": "Combine multiple PDF files into one PDF in your browser. Files are processed locally and are not uploaded.",
        "keyword": "merge PDF",
        "type": "pdf_merge",
    },
    "pdf-split": {
        "title": "PDF Split",
        "headline": "Split a PDF into separate pages",
        "description": "Split a PDF into individual page files directly in your browser without uploading the document.",
        "keyword": "split PDF",
        "type": "pdf_split",
    },
    "pdf-extract-pages": {
        "title": "PDF Page Extractor",
        "headline": "Extract pages from a PDF",
        "description": "Choose page numbers from a PDF and download a new PDF containing only those pages.",
        "keyword": "extract PDF pages",
        "type": "pdf_extract",
    },
    "pdf-rotate": {
        "title": "PDF Rotate",
        "headline": "Rotate PDF pages",
        "description": "Rotate all pages in a PDF by 90, 180, or 270 degrees and download the updated file.",
        "keyword": "rotate PDF",
        "type": "pdf_rotate",
    },
    "json-formatter": {
        "title": "JSON Formatter",
        "headline": "JSON formatter and validator",
        "description": "Format, validate, and minify JSON in your browser for APIs, configs, and debugging.",
        "keyword": "JSON formatter",
        "type": "json_formatter",
    },
    "base64-converter": {
        "title": "Base64 Converter",
        "headline": "Base64 encoder and decoder",
        "description": "Encode text to Base64 or decode Base64 back to readable text.",
        "keyword": "Base64 converter",
        "type": "base64_converter",
    },
    "url-encoder": {
        "title": "URL Encoder",
        "headline": "URL encoder and decoder",
        "description": "Encode or decode URLs, query strings, and text for safe use in web links.",
        "keyword": "URL encoder",
        "type": "url_encoder",
    },
    "hash-generator": {
        "title": "Hash Generator",
        "headline": "SHA hash generator",
        "description": "Generate SHA-256, SHA-384, or SHA-512 hashes from text in your browser.",
        "keyword": "hash generator",
        "type": "hash_generator",
    },
    "timestamp-converter": {
        "title": "Timestamp Converter",
        "headline": "Unix timestamp converter",
        "description": "Convert Unix timestamps to readable dates and convert dates back to Unix time.",
        "keyword": "timestamp converter",
        "type": "timestamp_converter",
    },
    "regex-tester": {
        "title": "Regex Tester",
        "headline": "Regex tester",
        "description": "Test a regular expression against sample text and view matches instantly.",
        "keyword": "regex tester",
        "type": "regex_tester",
    },
    "uuid-generator": {
        "title": "UUID Generator",
        "headline": "UUID generator",
        "description": "Generate random UUIDs for development, testing, mock data, and identifiers.",
        "keyword": "UUID generator",
        "type": "uuid_generator",
    },
    "text-diff": {
        "title": "Text Diff Checker",
        "headline": "Text diff checker",
        "description": "Compare two text blocks line by line and identify added, removed, and changed lines.",
        "keyword": "text diff checker",
        "type": "text_diff",
    },
    "image-resizer": {
        "title": "Image Resizer",
        "headline": "Image resizer",
        "description": "Resize JPG, PNG, and WebP images in your browser and download the resized file.",
        "keyword": "image resizer",
        "type": "image_resizer",
    },
    "image-compressor": {
        "title": "Image Compressor",
        "headline": "Image compressor",
        "description": "Reduce image file size by adjusting quality and exporting a smaller image from your browser.",
        "keyword": "image compressor",
        "type": "image_compressor",
    },
    "image-to-webp": {
        "title": "Image to WebP Converter",
        "headline": "Image to WebP converter",
        "description": "Convert JPG or PNG images to WebP format for smaller web-friendly files.",
        "keyword": "image to WebP",
        "type": "image_to_webp",
    },
    "qr-code-generator": {
        "title": "QR Code Generator",
        "headline": "QR code generator",
        "description": "Generate a QR code for a URL, text, email, phone number, or short message.",
        "keyword": "QR code generator",
        "type": "qr_code_generator",
    },
    "invoice-generator": {
        "title": "Invoice Generator",
        "headline": "Simple invoice generator",
        "description": "Create a simple invoice preview with item totals, tax, and a printable layout.",
        "keyword": "invoice generator",
        "type": "invoice_generator",
    },
    "markdown-previewer": {
        "title": "Markdown Previewer",
        "headline": "Markdown previewer",
        "description": "Write Markdown and preview headings, lists, bold text, links, and code blocks instantly.",
        "keyword": "Markdown previewer",
        "type": "markdown_previewer",
    },
    "jwt-decoder": {
        "title": "JWT Decoder",
        "headline": "JWT decoder",
        "description": "Decode a JSON Web Token header and payload in your browser without sending it to a server.",
        "keyword": "JWT decoder",
        "type": "jwt_decoder",
    },
    "csv-to-json": {
        "title": "CSV to JSON Converter",
        "headline": "CSV to JSON converter",
        "description": "Convert simple CSV data into JSON for APIs, spreadsheets, mock data, and developer workflows.",
        "keyword": "CSV to JSON",
        "type": "csv_to_json",
    },
    "xml-formatter": {
        "title": "XML Formatter",
        "headline": "XML formatter and validator",
        "description": "Format XML with readable indentation and check for basic XML parsing errors in your browser.",
        "keyword": "XML formatter",
        "type": "xml_formatter",
    },
    "html-formatter": {
        "title": "HTML Formatter",
        "headline": "HTML formatter",
        "description": "Format HTML markup into a more readable structure for editing, debugging, and quick cleanup.",
        "keyword": "HTML formatter",
        "type": "html_formatter",
    },
    "sql-formatter": {
        "title": "SQL Formatter",
        "headline": "SQL formatter",
        "description": "Make simple SQL queries easier to read by adding line breaks around common clauses and keywords.",
        "keyword": "SQL formatter",
        "type": "sql_formatter",
    },
    "color-converter": {
        "title": "Color Converter",
        "headline": "HEX, RGB, and HSL color converter",
        "description": "Convert colors between HEX, RGB, and HSL values for design, CSS, and front-end work.",
        "keyword": "color converter",
        "type": "color_converter",
    },
    "meta-tag-previewer": {
        "title": "Meta Tag Previewer",
        "headline": "Meta title and description previewer",
        "description": "Preview a search result snippet from a page title, meta description, and URL before publishing.",
        "keyword": "meta tag previewer",
        "type": "meta_tag_previewer",
    },
    "robots-txt-generator": {
        "title": "Robots.txt Generator",
        "headline": "Robots.txt generator",
        "description": "Generate a simple robots.txt file with allow, disallow, and sitemap lines for a website.",
        "keyword": "robots.txt generator",
        "type": "robots_txt_generator",
    },
    "lorem-ipsum-generator": {
        "title": "Lorem Ipsum Generator",
        "headline": "Lorem ipsum generator",
        "description": "Generate placeholder paragraphs, sentences, or words for layouts, mockups, and drafts.",
        "keyword": "lorem ipsum generator",
        "type": "lorem_ipsum_generator",
    },
    "keyword-density-checker": {
        "title": "Keyword Density Checker",
        "headline": "Keyword density checker",
        "description": "Check how often words appear in a text and estimate simple keyword density for content review.",
        "keyword": "keyword density checker",
        "type": "keyword_density_checker",
    },
}

TOOL_CATEGORIES = {
    "pdf": {
        "title": "PDF Tools",
        "headline": "Free PDF tools",
        "description": "Merge, split, extract, and rotate PDF files in your browser without uploading documents.",
    },
    "developer": {
        "title": "Developer Tools",
        "headline": "Free developer tools",
        "description": "Format JSON, encode Base64, test regex, decode JWTs, generate hashes, convert timestamps, and create UUIDs.",
    },
    "image": {
        "title": "Image Tools",
        "headline": "Free image tools",
        "description": "Resize, compress, and convert images to WebP directly in your browser.",
    },
    "business": {
        "title": "Business Tools",
        "headline": "Free business tools",
        "description": "Generate QR codes, invoices, and small business assets without creating an account.",
    },
    "text": {
        "title": "Text Tools",
        "headline": "Free text tools",
        "description": "Count words, convert case, repeat text, compare text, and prepare content quickly.",
    },
    "calculator": {
        "title": "Calculators",
        "headline": "Free online calculators",
        "description": "Calculate percentages, age, time, tips, and convert common units.",
    },
    "productivity": {
        "title": "Productivity Tools",
        "headline": "Free productivity tools",
        "description": "Use quick tools for focus sessions, habits, random choices, and daily decisions.",
    },
}

BLOG_POSTS = {
    "how-to-merge-pdf-files-online": {
        "title": "How to Merge PDF Files Online",
        "description": "A simple guide to combining PDF files in the browser without installing a desktop PDF editor.",
        "keyword": "merge PDF files online",
        "tool_slug": "pdf-merge",
        "category": "PDF",
        "intro": "Merging PDFs is useful when separate forms, scans, reports, or receipts need to become one file. A browser-based PDF merge tool is enough for simple page-level combining, especially when you do not need advanced editing.",
        "sections": [
            ("When merging PDFs helps", "Use PDF merging when you have several documents that belong together: a cover page and report, multiple receipts, scanned pages, or forms that should be sent as one attachment."),
            ("Before you start", "Put the files in the order you want, rename them clearly if needed, and check that each PDF opens correctly. If the order matters, add the files one by one in sequence."),
            ("Privacy and file handling", "For simple browser tools, files can be processed locally in the tab. That is useful for ordinary documents, but sensitive legal, medical, financial, or private records should still be handled carefully."),
            ("After downloading", "Open the merged PDF and scan the first and last pages. Check page order, orientation, file size, and whether every source document appears."),
        ],
        "steps": ["Open the PDF merge tool.", "Select two or more PDF files.", "Confirm the file order.", "Run the merge and download the combined PDF.", "Open the result before sending or archiving it."],
        "related_tools": ["pdf-merge", "pdf-split", "pdf-extract-pages", "pdf-rotate"],
    },
    "how-to-format-json-for-api-debugging": {
        "title": "How to Format JSON for API Debugging",
        "description": "Learn how formatted JSON helps you read API responses, config files, mock data, and logs.",
        "keyword": "format JSON",
        "tool_slug": "json-formatter",
        "category": "Developer",
        "intro": "Raw JSON is often difficult to inspect because it arrives as a long single line. Formatting JSON adds indentation and line breaks, making objects, arrays, strings, numbers, and nested fields easier to read.",
        "sections": [
            ("Why JSON formatting matters", "Readable JSON makes debugging faster. You can spot missing commas, unexpected field names, null values, nested arrays, and response shape changes before they become bigger problems."),
            ("Common places JSON appears", "Developers, analysts, and operators see JSON in API responses, webhooks, config files, logs, exported data, browser storage, and mock payloads."),
            ("Validation before sharing", "If JSON does not parse, fix the structural issue before pasting it into documentation, tickets, or tests. Common problems include trailing commas, unquoted keys, and mismatched brackets."),
            ("Minify when needed", "Formatted JSON is best for reading. Minified JSON is better when you need compact text for a URL field, config value, or small payload example."),
        ],
        "steps": ["Paste the JSON into the formatter.", "Click format to add indentation.", "Read any validation message.", "Copy the formatted result into your editor or notes.", "Use minify only when compact output is needed."],
        "related_tools": ["json-formatter", "csv-to-json", "xml-formatter", "base64-converter"],
    },
    "compress-images-before-uploading": {
        "title": "How to Compress Images Before Uploading",
        "description": "Reduce image file size for websites, email, forms, and marketplaces while keeping the image usable.",
        "keyword": "compress images",
        "tool_slug": "image-compressor",
        "category": "Image",
        "intro": "Large images slow down pages and can fail upload limits. Compressing an image lowers file size by changing quality, format, or both while keeping the dimensions useful for the task.",
        "sections": [
            ("When to compress images", "Compress images before uploading to websites, sending email attachments, submitting forms, listing products, or adding screenshots to documents."),
            ("Quality tradeoffs", "Lower quality usually means smaller files, but too much compression can create visible artifacts. For photos, start around 70 to 85 percent and check the result."),
            ("JPG vs WebP", "JPG is widely compatible and good for photos. WebP can be smaller for web use, but check whether the site or app you are uploading to accepts it."),
            ("Check the final file", "After compression, open the output image at normal viewing size. Confirm text, faces, product details, or important edges still look clear."),
        ],
        "steps": ["Open the image compressor.", "Choose the image file.", "Select JPG or WebP output.", "Set a quality level.", "Download and inspect the compressed image."],
        "related_tools": ["image-compressor", "image-resizer", "image-to-webp", "color-converter"],
    },
    "split-vs-extract-pdf-pages": {
        "title": "PDF Split vs Extract Pages: What Is the Difference?",
        "description": "Understand when to split every PDF page and when to extract only selected pages into a new file.",
        "keyword": "split PDF vs extract pages",
        "tool_slug": "pdf-extract-pages",
        "category": "PDF",
        "intro": "PDF split and PDF extract sound similar, but they solve different problems. Splitting usually turns every page into separate files. Extracting creates a new PDF from only the pages you choose.",
        "sections": [
            ("Use split when every page matters", "Splitting is helpful for scanned packets, batches of single-page forms, receipts, worksheets, or documents where each page needs to become its own file."),
            ("Use extract for selected pages", "Extraction is better when you only need pages 2-4 from a report, a single signed page, one chapter, or a small section from a larger PDF."),
            ("Watch page numbers", "PDF viewers count pages from 1, while some technical tools count from 0. A user-facing extractor should use normal page numbers such as 1, 3, or 5-7."),
            ("Keep the original", "Always keep the original PDF until you confirm the split or extracted result contains the correct pages."),
        ],
        "steps": ["Decide whether you need every page or selected pages.", "Use split for every page.", "Use extract for a page range.", "Download the new file or files.", "Open the output and verify page order."],
        "related_tools": ["pdf-split", "pdf-extract-pages", "pdf-merge", "pdf-rotate"],
    },
    "best-free-browser-tools-for-developers": {
        "title": "Best Free Browser Tools for Developers",
        "description": "A practical set of lightweight developer utilities for formatting, encoding, timestamps, UUIDs, hashes, regex, and tokens.",
        "keyword": "free browser tools for developers",
        "tool_slug": "json-formatter",
        "category": "Developer",
        "intro": "Small developer tasks do not always need a full IDE plugin or command-line workflow. Browser utilities are useful for quick checks while reading docs, testing APIs, writing tickets, or preparing examples.",
        "sections": [
            ("Data formatting tools", "JSON, XML, HTML, SQL, and CSV tools help make copied data readable before it goes into a code review, support ticket, or local test."),
            ("Encoding and decoding tools", "Base64, URL encoding, JWT decoding, and timestamp conversion are common tasks when inspecting APIs and web apps."),
            ("Generators and testers", "UUID generators, hash generators, and regex testers help create mock data, compare values, and validate text patterns."),
            ("Security habit", "Do not paste live secrets, production tokens, private keys, passwords, or confidential payloads into any tool unless you fully understand where the data goes."),
        ],
        "steps": ["Pick the smallest tool for the task.", "Use sample or non-sensitive data when possible.", "Check the result before copying it into code.", "Bookmark tools you use repeatedly.", "Move sensitive workflows into trusted local tooling."],
        "related_tools": ["json-formatter", "regex-tester", "uuid-generator", "jwt-decoder", "timestamp-converter", "hash-generator"],
    },
    "how-to-check-keyword-density-without-over-optimizing": {
        "title": "How to Check Keyword Density Without Over-Optimizing",
        "description": "Use keyword density as a simple review signal while keeping content readable and useful.",
        "keyword": "keyword density checker",
        "tool_slug": "keyword-density-checker",
        "category": "Text",
        "intro": "Keyword density can show whether a draft repeats the same words too often, but it should not be treated as a ranking formula. The goal is clear, useful writing that naturally covers the topic.",
        "sections": [
            ("What keyword density tells you", "A density check counts repeated words and estimates how often they appear compared with total word count. It can reveal accidental repetition or missing topic terms."),
            ("What it cannot tell you", "Keyword density does not prove that a page will rank. Search engines evaluate usefulness, intent match, links, structure, freshness, and many other signals."),
            ("Use it as an editing aid", "If one word appears too often, rewrite a few sentences. If important topic terms never appear, add clearer explanations rather than stuffing phrases."),
            ("Read the page aloud", "After checking density, read the content like a person. If it sounds forced, simplify it."),
        ],
        "steps": ["Paste your draft into the checker.", "Review the most repeated words.", "Look for unnatural repetition.", "Add missing terms only where they help the reader.", "Recheck after editing."],
        "related_tools": ["keyword-density-checker", "word-counter", "case-converter", "markdown-previewer"],
    },
}

BLOG_ENHANCEMENTS = {
    "how-to-merge-pdf-files-online": {
        "takeaway": "Use merge when several finished PDFs should travel as one document. The most common mistake is not the merge itself, but sending pages in the wrong order.",
        "scenario": "Example: you have a signed form, three receipts, and a cover note for a reimbursement request. Merge them into one PDF so the recipient does not have to open five attachments.",
        "checklist": ["File names are clear before selecting them.", "Pages are in the order the recipient expects.", "Every source PDF opens correctly.", "The merged file opens after download.", "The final file size is acceptable for email or upload limits."],
        "mistakes": ["Uploading the same PDF twice.", "Forgetting a cover page or signature page.", "Assuming the output order is correct without opening the result.", "Merging confidential files on a shared or untrusted device."],
        "comparison": [
            ("Merge", "Combine several PDFs into one file.", "Sending one complete packet."),
            ("Split", "Turn one PDF into separate page files.", "Separating scanned batches."),
            ("Extract", "Create a new PDF from selected pages.", "Sharing only pages 2-4 of a larger file."),
        ],
    },
    "how-to-format-json-for-api-debugging": {
        "takeaway": "Format JSON when you need to understand structure; minify JSON when you need compact output. Do not paste live secrets or production tokens.",
        "scenario": "Example: an API returns a one-line response and a field is missing in your app. Formatting the response lets you inspect nested objects, arrays, null values, and naming differences quickly.",
        "checklist": ["The JSON parses without errors.", "Nested arrays and objects are easy to scan.", "Unexpected null or empty values are visible.", "Sensitive tokens are removed before sharing.", "The formatted result matches the original data structure."],
        "mistakes": ["Treating JavaScript object syntax as valid JSON.", "Leaving trailing commas from copied code.", "Sharing real API keys in examples.", "Changing the payload while trying to format it."],
        "comparison": [
            ("Format", "Adds indentation and line breaks.", "Reading and debugging."),
            ("Validate", "Checks whether the JSON can be parsed.", "Finding syntax errors."),
            ("Minify", "Removes unnecessary whitespace.", "Compact payload examples."),
        ],
    },
    "compress-images-before-uploading": {
        "takeaway": "Compress images enough to meet upload or page-speed needs, but not so much that text, product details, or faces become unclear.",
        "scenario": "Example: a form rejects a 7 MB photo because the limit is 2 MB. Compress the image as JPG or WebP, download it, and inspect the important details before uploading again.",
        "checklist": ["The output file is below the upload limit.", "Important text or product details remain readable.", "The format is accepted by the target site.", "The image dimensions still fit the layout.", "The original file is kept until the compressed version is approved."],
        "mistakes": ["Using very low quality for images with small text.", "Choosing WebP when the upload form only accepts JPG or PNG.", "Compressing repeatedly from an already compressed file.", "Ignoring dimensions when file size is not the only issue."],
        "comparison": [
            ("Compress", "Reduce file size by changing quality or format.", "Meeting upload limits."),
            ("Resize", "Change pixel width and height.", "Fitting a layout or profile image."),
            ("Convert", "Change file format.", "Creating WebP or JPG versions."),
        ],
    },
    "split-vs-extract-pdf-pages": {
        "takeaway": "Split is for every page. Extract is for chosen pages. If you only need a few pages from a long file, extraction is usually cleaner.",
        "scenario": "Example: a 40-page packet includes a 3-page agreement you need to email. Extract pages 12-14 instead of splitting the entire file into 40 separate PDFs.",
        "checklist": ["You know the exact page numbers.", "The original PDF is saved safely.", "The output contains only the needed pages.", "The page order is correct.", "The output file name explains what was extracted."],
        "mistakes": ["Splitting a large PDF when only three pages are needed.", "Entering the wrong page range.", "Deleting the original before checking the output.", "Confusing printed page labels with PDF viewer page numbers."],
        "comparison": [
            ("Split", "Creates separate output for every page.", "Scanned packets and batches."),
            ("Extract", "Creates one PDF from selected pages.", "Sharing a section."),
            ("Rotate", "Changes page orientation.", "Fixing sideways scans."),
        ],
    },
    "best-free-browser-tools-for-developers": {
        "takeaway": "Browser developer tools are best for quick inspection and examples. For secrets, production payloads, and regulated data, use trusted local tooling.",
        "scenario": "Example: while writing an API ticket, you need to format a JSON response, decode a timestamp, generate a UUID for sample data, and test a small regex. Browser utilities can handle those small tasks without switching context.",
        "checklist": ["Use sample data when possible.", "Remove secrets before decoding or formatting.", "Copy results into tests only after checking them.", "Bookmark tools that save repeated lookup time.", "Use local scripts for sensitive or automated workflows."],
        "mistakes": ["Pasting production JWTs or API keys.", "Trusting a regex after one tiny example.", "Using generated UUIDs as proof of uniqueness beyond their intended purpose.", "Forgetting timezone differences when reading timestamps."],
        "comparison": [
            ("Formatter", "Makes data easier to read.", "JSON, XML, SQL, HTML."),
            ("Converter", "Changes representation.", "Base64, URL encoding, timestamps."),
            ("Generator", "Creates sample values.", "UUIDs, hashes, passwords."),
        ],
    },
    "how-to-check-keyword-density-without-over-optimizing": {
        "takeaway": "Keyword density is a review signal, not a ranking recipe. Use it to catch awkward repetition and missing topic coverage.",
        "scenario": "Example: a product page repeats the same phrase in every paragraph. A density check makes the repetition visible so you can replace some mentions with clearer explanations or related terms.",
        "checklist": ["The main topic appears naturally.", "Repeated words do not make the page sound robotic.", "Important related terms are covered where useful.", "Headings match what readers are trying to solve.", "The final draft still reads well aloud."],
        "mistakes": ["Chasing a fixed percentage.", "Adding keywords where they do not help the reader.", "Ignoring search intent and usefulness.", "Removing necessary repeated terms just to lower a number."],
        "comparison": [
            ("Density", "How often a word appears.", "Finding repetition."),
            ("Coverage", "Whether related ideas are explained.", "Making content useful."),
            ("Readability", "How naturally the page reads.", "Keeping users engaged."),
        ],
    },
}

for _slug, _enhancement in BLOG_ENHANCEMENTS.items():
    if _slug in BLOG_POSTS:
        BLOG_POSTS[_slug].update(_enhancement)

SCHEDULED_BLOG_POSTS = {
    "how-to-resize-an-image-for-a-profile-picture": {
        "publish_date": "2026-06-17",
        "title": "How to Resize an Image for a Profile Picture",
        "description": "Resize an image for profiles, resumes, forms, and account pages without making it blurry or awkwardly cropped.",
        "keyword": "resize image for profile picture",
        "tool_slug": "image-resizer",
        "category": "Image",
        "intro": "Profile pictures often fail because the image is too large, too small, or the wrong shape. Resizing helps match the required pixel dimensions before upload.",
        "takeaway": "Resize for dimensions first, then compress for file size. If the site asks for a square image, start with a square crop or centered subject.",
        "scenario": "Example: a job portal asks for a 400 by 400 pixel profile image under 1 MB. Resize the photo to a square, export it, and check that your face or subject remains centered.",
        "steps": ["Open the image resizer.", "Choose the source image.", "Enter the target width and height.", "Export as JPG, PNG, or WebP.", "Open the result and confirm it still looks sharp."],
        "sections": [
            ("Start with the target size", "Look for the exact upload requirement before resizing. Common profile images are square, but forms and resumes may ask for different dimensions."),
            ("Avoid stretching", "If the original image is wide and the target is square, resizing alone may distort the image. Use a centered crop first when the subject matters."),
            ("Choose the right format", "JPG is usually fine for photos. PNG is better for graphics with sharp edges or transparency. WebP is useful for web pages when accepted."),
            ("Check file size after resizing", "A smaller image dimension often lowers file size, but you may still need compression if the upload limit is strict."),
        ],
        "checklist": ["Target width and height are known.", "The subject is centered.", "The image is not stretched.", "The output format is accepted.", "The final file size fits the upload limit."],
        "mistakes": ["Changing only file size when the site requires exact dimensions.", "Stretching a wide image into a square.", "Using WebP on a form that only accepts JPG or PNG.", "Uploading without checking how the image appears at small size."],
        "comparison": [("Resize", "Change pixel dimensions.", "Profile image requirements."), ("Compress", "Lower file size.", "Upload limits."), ("Convert", "Change file format.", "Compatibility.")],
        "related_tools": ["image-resizer", "image-compressor", "image-to-webp", "color-converter"],
    },
    "xml-vs-json-when-to-use-each-format": {
        "publish_date": "2026-06-24",
        "title": "XML vs JSON: When to Use Each Format",
        "description": "A practical comparison of XML and JSON for APIs, config files, exports, and debugging.",
        "keyword": "XML vs JSON",
        "tool_slug": "xml-formatter",
        "category": "Developer",
        "intro": "XML and JSON both store structured data, but they feel different in everyday work. JSON is common in modern APIs, while XML still appears in documents, feeds, enterprise systems, and configuration files.",
        "takeaway": "Use JSON when you want compact API-friendly data. Use XML when the system expects tags, attributes, document structure, or older integration formats.",
        "scenario": "Example: a webhook response may arrive as JSON, while a sitemap, RSS feed, or legacy vendor export may arrive as XML. Formatting each one makes the structure easier to inspect.",
        "steps": ["Identify the format you received.", "Use a JSON formatter for JSON payloads.", "Use an XML formatter for tagged documents.", "Validate before editing.", "Keep an unchanged copy of the original data."],
        "sections": [
            ("JSON strengths", "JSON is compact, easy to read after formatting, and maps naturally to arrays, objects, strings, numbers, booleans, and null values."),
            ("XML strengths", "XML supports tags, attributes, namespaces, and document-style structures. It remains common in feeds, sitemaps, office files, and enterprise integrations."),
            ("Debugging habit", "Do not guess the format. A JSON parser will not validate XML, and an XML parser will not validate JSON."),
            ("Editing safely", "Small syntax changes can break either format. Format first, edit carefully, then validate again."),
        ],
        "checklist": ["The format is identified correctly.", "The data validates after formatting.", "Important nested fields are visible.", "No credentials or private payloads are shared.", "The original raw data is kept."],
        "mistakes": ["Pasting XML into a JSON formatter.", "Removing required XML attributes.", "Leaving invalid trailing commas in JSON.", "Assuming both formats behave the same in an API."],
        "comparison": [("JSON", "Compact object and array data.", "Modern APIs and app config."), ("XML", "Tagged document-style data.", "Feeds, sitemaps, legacy systems."), ("CSV", "Rows and columns.", "Simple spreadsheet exports.")],
        "related_tools": ["xml-formatter", "json-formatter", "html-formatter", "csv-to-json"],
    },
    "robots-txt-basics-for-small-websites": {
        "publish_date": "2026-07-01",
        "title": "Robots.txt Basics for Small Websites",
        "description": "Learn what robots.txt can and cannot do, and how to create a simple file for a small website.",
        "keyword": "robots.txt basics",
        "tool_slug": "robots-txt-generator",
        "category": "Developer",
        "intro": "A robots.txt file gives crawler instructions for a website. It can point to a sitemap and request that crawlers avoid certain paths, but it is not a security tool.",
        "takeaway": "Use robots.txt for crawl guidance, not privacy. Anything truly private should require authentication and should not be publicly accessible.",
        "scenario": "Example: a small site may allow all crawlers, disallow an admin path, and include a sitemap URL so search engines can discover public pages more easily.",
        "steps": ["Choose whether crawlers should access the site.", "Add disallow paths only when needed.", "Include the sitemap URL.", "Upload the file at /robots.txt.", "Test the file after publishing."],
        "sections": [
            ("What robots.txt does", "It tells compliant crawlers which paths they should avoid and where the sitemap can be found."),
            ("What robots.txt does not do", "It does not hide private information, block users, require login, or remove pages that are already indexed."),
            ("Simple default", "For most public sites, allowing all crawlers and listing the sitemap is a reasonable starting point."),
            ("Be careful with disallow", "Blocking important CSS, JavaScript, images, or content paths can make search engines understand pages less accurately."),
        ],
        "checklist": ["The file is available at /robots.txt.", "The sitemap URL is correct.", "Important public pages are not blocked.", "Private content is protected by access control.", "The syntax uses one instruction per line."],
        "mistakes": ["Using robots.txt as a password.", "Blocking the entire site by accident.", "Adding paths that do not exist.", "Forgetting to update the sitemap URL after changing domains."],
        "comparison": [("robots.txt", "Crawler guidance.", "Crawl rules and sitemap location."), ("noindex", "Indexing instruction.", "Keeping a page out of search results."), ("login", "Access control.", "Protecting private content.")],
        "related_tools": ["robots-txt-generator", "meta-tag-previewer", "keyword-density-checker", "url-encoder"],
    },
    "qr-code-ideas-for-small-businesses": {
        "publish_date": "2026-07-08",
        "title": "QR Code Ideas for Small Businesses",
        "description": "Practical QR code uses for menus, invoices, events, feedback forms, contact pages, and local promotions.",
        "keyword": "QR code ideas for small businesses",
        "tool_slug": "qr-code-generator",
        "category": "Business",
        "intro": "QR codes are useful when someone needs to move from a physical place to a digital page quickly. The best QR codes point to simple, mobile-friendly destinations.",
        "takeaway": "A QR code is only as useful as the page behind it. Use short, clear destinations and test the code on multiple phones before printing.",
        "scenario": "Example: a cafe can place a QR code on a counter sign that links to a menu, review form, loyalty signup, or event page.",
        "steps": ["Choose one clear destination.", "Generate the QR code.", "Test it on multiple phones.", "Print with enough white space around it.", "Add a short label that explains where it goes."],
        "sections": [
            ("Good QR destinations", "Menus, appointment pages, feedback forms, invoices, payment pages, contact cards, event registration, and product instructions work well."),
            ("Keep the page mobile-friendly", "Most QR scans happen on phones. Avoid pages that require pinching, long typing, or desktop-only layouts."),
            ("Add context", "A QR code without a label is easy to ignore. Add a short phrase such as Scan for menu or Scan to leave feedback."),
            ("Test before printing", "Printed QR codes should be large enough, high contrast, and surrounded by white space so cameras can read them quickly."),
        ],
        "checklist": ["The destination URL is correct.", "The page works on mobile.", "The QR code scans from printed size.", "The label explains the benefit.", "The code is not placed where glare or folds make scanning hard."],
        "mistakes": ["Linking to a slow or confusing page.", "Printing the QR code too small.", "Using low contrast colors.", "Forgetting to test after changing the destination page."],
        "comparison": [("Menu QR", "Links to food or service lists.", "Restaurants and cafes."), ("Feedback QR", "Links to a form.", "Customer reviews."), ("Payment QR", "Links to checkout.", "Invoices and counters.")],
        "related_tools": ["qr-code-generator", "invoice-generator", "url-encoder", "meta-tag-previewer"],
    },
    "how-to-convert-csv-to-json-for-mock-data": {
        "publish_date": "2026-07-15",
        "title": "How to Convert CSV to JSON for Mock Data",
        "description": "Turn simple spreadsheet-style rows into JSON for API examples, prototypes, demos, and test data.",
        "keyword": "CSV to JSON mock data",
        "tool_slug": "csv-to-json",
        "category": "Developer",
        "intro": "CSV is easy to edit in a spreadsheet, while JSON is easier to use in APIs and front-end prototypes. Converting CSV to JSON helps bridge those workflows.",
        "takeaway": "Use CSV when humans need to edit rows. Convert to JSON when an app, API, or prototype needs structured objects.",
        "scenario": "Example: you list product names, prices, and categories in a spreadsheet, then convert the rows into JSON for a quick mock API response.",
        "steps": ["Put field names in the first CSV row.", "Add one item per row.", "Open the CSV to JSON converter.", "Paste the CSV and convert it.", "Check that each JSON object has the expected keys."],
        "sections": [
            ("Start with clean headers", "The first row usually becomes the JSON object keys. Use clear names such as name, price, category, and status."),
            ("Keep rows consistent", "CSV works best when each row has the same number of columns. Missing cells can create empty values in the JSON output."),
            ("Use simple values first", "Avoid commas inside cells unless your CSV is properly quoted. Simple mock data is easier to convert and inspect."),
            ("Validate the result", "After conversion, scan the JSON for missing keys, wrong values, and accidental extra columns."),
        ],
        "checklist": ["Headers are short and clear.", "Rows use the same column order.", "Important blank cells are intentional.", "The JSON parses correctly.", "The result is sample data, not private customer data."],
        "mistakes": ["Forgetting the header row.", "Using commas inside unquoted values.", "Mixing different row structures.", "Copying private spreadsheet data into a public example."],
        "comparison": [("CSV", "Rows and columns.", "Spreadsheet editing."), ("JSON", "Objects and arrays.", "APIs and prototypes."), ("XML", "Tagged structured data.", "Feeds and legacy systems.")],
        "related_tools": ["csv-to-json", "json-formatter", "xml-formatter", "text-diff"],
    },
    "how-to-preview-meta-title-and-description": {
        "publish_date": "2026-07-22",
        "title": "How to Preview a Meta Title and Description",
        "description": "Check whether a page title and meta description are clear before publishing a page.",
        "keyword": "meta title and description preview",
        "tool_slug": "meta-tag-previewer",
        "category": "Text",
        "intro": "A title and meta description are often the first text a searcher sees. Previewing them helps you spot vague wording, truncation risk, and missing intent before publishing.",
        "takeaway": "Write the title for the searcher's task, not just the page owner. Use the description to explain the concrete value of clicking.",
        "scenario": "Example: a tool page called Formatter is vague. A title like JSON Formatter and Validator is clearer because it names the exact task.",
        "steps": ["Enter the page URL.", "Write a specific title.", "Add a plain-language description.", "Preview the snippet.", "Revise until the result is clear and not overstuffed."],
        "sections": [
            ("Make the title specific", "A good title names the tool, guide, product, or answer clearly. Avoid generic labels that could apply to many pages."),
            ("Use the description for context", "The description should summarize what the visitor can do or learn, not repeat the title word for word."),
            ("Do not promise too much", "A clickbait title may get attention, but it can increase bounce if the page does not deliver."),
            ("Remember search engines may rewrite snippets", "A preview is a planning aid. Search engines can still choose different text from the page."),
        ],
        "checklist": ["The title names the main topic.", "The description explains why the page is useful.", "The text is readable on mobile.", "Important words appear naturally.", "The snippet matches the actual page content."],
        "mistakes": ["Stuffing repeated keywords.", "Using the same title on many pages.", "Writing a vague description.", "Promising features the page does not have."],
        "comparison": [("Title", "Main search result headline.", "Topic and click clarity."), ("Description", "Supporting snippet text.", "Reason to visit."), ("URL", "Destination signal.", "Trust and context.")],
        "related_tools": ["meta-tag-previewer", "keyword-density-checker", "word-counter", "robots-txt-generator"],
    },
    "how-to-use-a-text-diff-checker": {
        "publish_date": "2026-07-29",
        "title": "How to Use a Text Diff Checker",
        "description": "Compare two versions of text to find edits, missing lines, changed wording, and accidental deletions.",
        "keyword": "text diff checker",
        "tool_slug": "text-diff",
        "category": "Text",
        "intro": "A text diff checker helps you compare two versions side by side. It is useful for drafts, code snippets, contracts, documentation, email edits, and copied content.",
        "takeaway": "Use a diff checker whenever small wording changes matter. It is faster than rereading two similar blocks manually.",
        "scenario": "Example: a client sends an updated paragraph and says only a few lines changed. Paste the old and new versions into a diff checker to see exactly what moved.",
        "steps": ["Paste the original text on the left.", "Paste the changed text on the right.", "Run the comparison.", "Review added, removed, and changed lines.", "Copy the final approved version only after checking the differences."],
        "sections": [
            ("When diff checking helps", "Use it for document revisions, release notes, support replies, code snippets, privacy text, and any text where a small edit can change meaning."),
            ("Check line breaks", "Diff tools often compare line by line. If everything is one long paragraph, add line breaks around logical sections first."),
            ("Look for accidental deletions", "The most useful diff is often not the changed word, but the line that disappeared unexpectedly."),
            ("Use it before publishing", "A final diff can catch edits that were made during review but never intended to go live."),
        ],
        "checklist": ["Original and revised text are pasted into the correct sides.", "Line breaks make the comparison readable.", "Removed lines are intentional.", "Changed wording keeps the same meaning.", "The approved final version is copied from the right place."],
        "mistakes": ["Comparing two texts with different formatting only.", "Ignoring removed sections.", "Pasting confidential text into an untrusted tool.", "Assuming all changes are visible without scrolling."],
        "comparison": [("Diff", "Shows text changes.", "Reviewing edits."), ("Word count", "Measures length.", "Checking size limits."), ("Case converter", "Changes capitalization.", "Formatting text.")],
        "related_tools": ["text-diff", "word-counter", "case-converter", "markdown-previewer"],
    },
    "how-to-generate-an-invoice-for-freelance-work": {
        "publish_date": "2026-08-05",
        "title": "How to Generate a Simple Invoice for Freelance Work",
        "description": "Create a clean invoice with bill-to details, item lines, totals, and tax without overcomplicating the process.",
        "keyword": "simple invoice generator for freelance work",
        "tool_slug": "invoice-generator",
        "category": "Business",
        "intro": "A simple invoice helps clients understand what they are paying for, how much is due, and who issued the bill. It does not need to be complex for small jobs.",
        "takeaway": "A useful invoice is clear, complete, and easy to verify. Include who billed whom, what was delivered, item amounts, tax if needed, and the total.",
        "scenario": "Example: a freelancer completes a logo update and two landing page edits. Each line item can show the task, quantity, price, and total.",
        "steps": ["Enter your name or business.", "Enter the client or bill-to name.", "Add each item on its own line.", "Set tax if applicable.", "Review the preview before sending."],
        "sections": [
            ("Keep line items specific", "Instead of writing work, name the deliverable: landing page copy edit, consultation hour, image resize batch, or monthly support."),
            ("Check totals", "Small invoice errors are easy to miss. Confirm quantity, price, subtotal, tax, and final total."),
            ("Add payment context separately", "If you need payment terms, bank details, or a due date, include them in your email or invoice notes when available."),
            ("Store a copy", "Keep a copy of the invoice and related communication so you can answer questions later."),
        ],
        "checklist": ["Your sender details are clear.", "The client name is correct.", "Each item has a price.", "Tax is applied only when appropriate.", "The total matches the agreement."],
        "mistakes": ["Using vague item descriptions.", "Forgetting tax or applying it incorrectly.", "Sending without checking totals.", "Not keeping a copy for records."],
        "comparison": [("Invoice", "Requests payment.", "Completed work."), ("Quote", "Estimates cost.", "Before approval."), ("Receipt", "Confirms payment.", "After payment.")],
        "related_tools": ["invoice-generator", "qr-code-generator", "percentage-calculator", "tip-calculator"],
    },
    "how-to-convert-images-to-webp": {
        "publish_date": "2026-08-12",
        "title": "How to Convert Images to WebP",
        "description": "Convert JPG or PNG images to WebP for smaller web-friendly files and faster pages.",
        "keyword": "convert image to WebP",
        "tool_slug": "image-to-webp",
        "category": "Image",
        "intro": "WebP is a modern image format that can reduce file size while keeping good visual quality. It is useful for websites, landing pages, and image-heavy content.",
        "takeaway": "Use WebP for web performance when your platform supports it. Keep JPG or PNG copies when compatibility matters.",
        "scenario": "Example: a blog post has several large PNG screenshots. Converting them to WebP can reduce page weight and make the page load faster.",
        "steps": ["Open the image to WebP converter.", "Choose a JPG or PNG image.", "Convert the file.", "Download the WebP output.", "Preview it in the browser or upload target."],
        "sections": [
            ("Why WebP helps", "Smaller images can improve page speed, reduce bandwidth, and make pages feel faster on mobile connections."),
            ("When not to use WebP", "Some older tools, forms, or workflows may not accept WebP. Use JPG or PNG if compatibility is more important than size."),
            ("Keep originals", "Always keep the original image in case you need to edit it later or export another format."),
            ("Combine with resizing", "If the image dimensions are far larger than needed, resize first and then convert or compress."),
        ],
        "checklist": ["The target platform accepts WebP.", "The image still looks clear.", "The file size is lower than before.", "The original is saved.", "The dimensions fit the page layout."],
        "mistakes": ["Using WebP where only JPG or PNG is allowed.", "Converting an already tiny image with no benefit.", "Deleting the original too early.", "Ignoring dimensions and only changing format."],
        "comparison": [("WebP", "Smaller modern web image.", "Web pages."), ("JPG", "Common photo format.", "Compatibility."), ("PNG", "Sharp graphics and transparency.", "Logos and UI screenshots.")],
        "related_tools": ["image-to-webp", "image-compressor", "image-resizer", "color-converter"],
    },
    "unix-timestamp-converter-guide": {
        "publish_date": "2026-08-19",
        "title": "Unix Timestamp Converter Guide",
        "description": "Understand Unix timestamps and convert them into readable dates for logs, APIs, events, and debugging.",
        "keyword": "Unix timestamp converter",
        "tool_slug": "timestamp-converter",
        "category": "Developer",
        "intro": "Unix timestamps represent time as a number. They are common in APIs, logs, databases, analytics events, and scheduled jobs.",
        "takeaway": "Always check whether a timestamp is in seconds or milliseconds, and be careful with timezone assumptions.",
        "scenario": "Example: an API returns 1781904000 and you need to know when an event happens. A timestamp converter turns the number into a readable date.",
        "steps": ["Copy the timestamp.", "Check whether it has 10 digits or 13 digits.", "Paste it into the converter.", "Review the readable date.", "Confirm the expected timezone."],
        "sections": [
            ("Seconds vs milliseconds", "Many Unix timestamps use seconds, while JavaScript often uses milliseconds. A 10-digit value is usually seconds; a 13-digit value is often milliseconds."),
            ("Timezone confusion", "A timestamp points to a moment in time, but the displayed date can change depending on timezone."),
            ("Where timestamps appear", "Look for them in logs, API payloads, cookies, analytics exports, database fields, and job schedules."),
            ("Convert both directions", "Sometimes you need to read a timestamp; other times you need to create one from a date for testing."),
        ],
        "checklist": ["The value is seconds or milliseconds.", "The converted date matches expected timezone.", "The timestamp is copied fully.", "The result is checked against nearby events.", "The final value is not confused with an ID."],
        "mistakes": ["Treating milliseconds as seconds.", "Ignoring timezone differences.", "Copying only part of a timestamp.", "Assuming every long number is a timestamp."],
        "comparison": [("Seconds", "Usually 10 digits.", "Unix time APIs."), ("Milliseconds", "Usually 13 digits.", "JavaScript dates."), ("ISO date", "Readable date string.", "Human review and logs.")],
        "related_tools": ["timestamp-converter", "json-formatter", "uuid-generator", "url-encoder"],
    },
    "how-to-test-a-regular-expression": {
        "publish_date": "2026-08-26",
        "title": "How to Test a Regular Expression",
        "description": "Test regex patterns against sample text before using them in forms, scripts, filters, and validation rules.",
        "keyword": "regex tester",
        "tool_slug": "regex-tester",
        "category": "Developer",
        "intro": "Regular expressions are powerful, but small pattern changes can match too much or too little. Testing against realistic examples helps avoid mistakes.",
        "takeaway": "A regex is only as good as the examples you test. Include matches, non-matches, edge cases, and messy real-world input.",
        "scenario": "Example: you want to find order IDs in support messages. Test valid IDs, invalid IDs, IDs inside sentences, and messages with no ID before relying on the pattern.",
        "steps": ["Write a first version of the pattern.", "Paste realistic sample text.", "Check the matches.", "Add examples that should not match.", "Revise the pattern until both sets behave correctly."],
        "sections": [
            ("Start simple", "Begin with the smallest pattern that works, then add constraints only when needed."),
            ("Use realistic examples", "A pattern that works on one clean example may fail on punctuation, line breaks, uppercase letters, or extra spaces."),
            ("Watch greedy matches", "Patterns can accidentally capture too much text. Test with multiple examples in the same input."),
            ("Validate in the target environment", "Regex behavior can differ slightly across languages and tools, so confirm important patterns where they will run."),
        ],
        "checklist": ["Valid examples match.", "Invalid examples do not match.", "Uppercase and lowercase behavior is intentional.", "Line breaks are handled correctly.", "The pattern is tested in the target app or language."],
        "mistakes": ["Testing only one perfect example.", "Forgetting to escape special characters.", "Using a pattern that is too broad.", "Assuming every regex engine behaves exactly the same."],
        "comparison": [("Regex", "Pattern matching.", "Finding structured text."), ("Text diff", "Change detection.", "Comparing versions."), ("Word count", "Length checking.", "Draft review.")],
        "related_tools": ["regex-tester", "text-diff", "json-formatter", "url-encoder"],
    },
}

BLOG_POSTS.update(SCHEDULED_BLOG_POSTS)


def _today_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _is_blog_published(post: dict) -> bool:
    return post.get("publish_date", "2026-06-10") <= _today_iso()


def _published_blog_posts() -> dict[str, dict]:
    published = {slug: post for slug, post in BLOG_POSTS.items() if _is_blog_published(post)}
    return dict(sorted(published.items(), key=lambda item: item[1].get("publish_date", "2026-06-10"), reverse=True))


@app.context_processor
def inject_globals():
    lang = session.get("lang", DEFAULT_LANG)
    return {
        "UI": UI,
        "LANG_CONFIG": LANG_CONFIG,
        "lang": lang,
        "t": lambda key: t(key, lang),
        "tc": lambda cid: tc(cid, lang),
        "tcat": lambda cat: tcat(cat, lang),
        "app_url": APP_URL,
        "adsense_client": os.environ.get("ADSENSE_CLIENT", DEFAULT_ADSENSE_CLIENT),
        "adsense_bottom_slot": os.environ.get("ADSENSE_SLOT_BOTTOM", ""),
        "contact_email": os.environ.get("CONTACT_EMAIL", "contact@example.com"),
    }


# ────────────────────────────────────────────────
# 직업별 상세 정보 (연봉 실데이터, 취업 경로)
# 출처: 고용노동부 임금정보시스템, 커리어넷 (2024 기준)
# ────────────────────────────────────────────────
CAREER_DETAIL_DB = {
    "software_dev":      {"salary_range": "3,500~7,000만원 (신입~5년차)", "career_path": ["컴퓨터공학 전공 or 부트캠프", "공개 채용 / 인턴십 지원", "주니어 개발자 1~3년", "시니어 / 풀스택 3~7년", "테크리드 or 창업"]},
    "data_scientist":    {"salary_range": "4,000~9,000만원", "career_path": ["통계·수학·CS 전공 (대학원 권장)", "Kaggle 등 포트폴리오 구축", "주니어 분석가 2~3년", "시니어 데이터 과학자", "ML 리서처 or 수석 과학자"]},
    "ai_engineer":       {"salary_range": "4,500~1억원+", "career_path": ["CS/수학 대학원", "논문 및 오픈소스 기여", "AI 스타트업 or 대기업 연구소", "ML 엔지니어 → 리서처", "AI 연구소 팀장"]},
    "doctor":            {"salary_range": "1억~2억5천만원 (전문의 기준)", "career_path": ["의과대학 6년", "인턴 1년 + 레지던트 4년", "전문의 자격 취득", "개원 or 대학병원 교수 트랙"]},
    "lawyer":            {"salary_range": "4,000~1억5천만원 (경력별)", "career_path": ["법학전문대학원(로스쿨) 3년", "변호사 시험 합격", "로펌 or 검사/판사 임용", "파트너 변호사 or 전문 분야 개업"]},
    "teacher":           {"salary_range": "3,200~5,500만원 (공립 기준)", "career_path": ["사범대 or 교직 이수", "임용고시 준비·합격", "기간제 교사 → 정교사", "수석교사 or 교감·교장"]},
    "nurse":             {"salary_range": "3,000~5,000만원", "career_path": ["간호학과 4년", "국가시험 합격 (간호사 면허)", "병원 신규 간호사", "전문 간호사 자격 취득", "수간호사 or 관리직"]},
    "pharmacist":        {"salary_range": "4,000~7,000만원", "career_path": ["약학대학 6년", "약사 면허 취득", "약국 취업 or 병원 약사", "개인 약국 창업"]},
    "architect":         {"salary_range": "3,000~7,000만원", "career_path": ["건축학과 5년", "건축사 시험 준비 (실무 3년)", "건축사 자격 취득", "설계사무소 or 건설사"]},
    "accountant":        {"salary_range": "3,500~8,000만원 (CPA 기준)", "career_path": ["경영·회계학과", "공인회계사(CPA) 시험", "회계법인 입사 (Big4 등)", "파트너 or CFO 트랙"]},
    "journalist":        {"salary_range": "3,000~6,000만원", "career_path": ["언론학·국문학 전공", "방송·신문사 공채 준비", "수습기자 1년", "취재기자 → 데스크 → 부장"]},
    "designer_graphic":  {"salary_range": "2,500~5,500만원", "career_path": ["시각디자인 전공 or 독학", "포트폴리오 구축", "디자인 에이전시 or 인하우스", "시니어 디자이너 / 아트디렉터"]},
    "musician":          {"salary_range": "불규칙 (무대·음반 수입 중심)", "career_path": ["음악 전공 or 독학 (재능 필수)", "콩쿠르·오디션 참가", "연주·레코딩 활동", "앙상블 or 솔로 무대", "교수직 병행 가능"]},
    "chef":              {"salary_range": "2,200~6,000만원 (경력별)", "career_path": ["조리학과 or 요리학원", "레스토랑 보조 요리사", "수셰프(부주방장)", "총주방장 or 오너셰프"]},
    "researcher":        {"salary_range": "4,000~8,000만원 (정부출연연 기준)", "career_path": ["이공계 대학원 (박사 권장)", "포스트닥터(포닥)", "연구소 입소 or 교수 공채", "책임연구원 or 부교수"]},
    "professor":         {"salary_range": "5,000~9,000만원", "career_path": ["박사 학위 취득", "포닥/연구원 경험", "신진교수 공개채용 (경쟁률 높음)", "조교수 → 부교수 → 정교수"]},
    "police":            {"salary_range": "3,000~5,500만원", "career_path": ["경찰대학 or 경찰공무원 채용시험", "순경 임용", "경장 → 경사 → 경위 (승진시험)", "경찰서 각 부서 순환 근무"]},
    "firefighter":       {"salary_range": "3,000~5,200만원", "career_path": ["소방공무원 채용시험 합격", "소방사 임용 (체력 필수)", "소방장 → 소방위 승진", "구조대·구급대 등 특수부서"]},
    "social_worker":     {"salary_range": "2,500~4,000만원", "career_path": ["사회복지학과", "사회복지사 1급 자격증", "복지관·NGO 취업", "시설장 or 전문 상담사"]},
    "counselor":         {"salary_range": "2,800~5,000만원", "career_path": ["심리학·상담학 전공 (석사 권장)", "임상심리사·상담심리사 자격", "상담센터·학교상담 취업", "사설 상담소 개업"]},
    "financial_analyst": {"salary_range": "4,000~1억원+ (성과급 포함)", "career_path": ["경제·경영·수학 전공", "증권사·투자은행 인턴", "애널리스트 CFA 취득", "선임 애널리스트 / 펀드매니저"]},
    "marketing_manager": {"salary_range": "3,500~7,000만원", "career_path": ["경영·광고·미디어 전공", "마케팅 인턴십 경험", "대리 → 과장 → 마케팅 팀장", "CMO (최고마케팅책임자)"]},
    "entrepreneur":      {"salary_range": "불규칙 (초기 낮음→성공 시 무제한)", "career_path": ["아이디어·시장조사", "팀 구성 + 투자 유치 (AC/VC)", "MVP 출시 → 피드백 반복", "스케일업 → 투자 시리즈 A/B", "IPO or M&A 엑싯"]},
    "pilot":             {"salary_range": "7,000만~1억5천만원 (항공사 기준)", "career_path": ["항공운항학과 or 공군 조종사", "자가용 조종사(PPL) → 계기비행(IR) → 사업용(CPL)", "부기장 채용 (500시간+)", "기장 승격 (3,000시간+)"]},
    "dentist":           {"salary_range": "8,000만~2억원", "career_path": ["치과대학 6년", "치과의사 면허 취득", "인턴·레지던트 (전문의 선택)", "치과 개원 or 대학병원 교수"]},
    "clinical_psychologist": {"salary_range": "3,000~5,500만원", "career_path": ["심리학 전공 (석사·박사 권장)", "임상심리사 2급→1급 자격", "병원·센터 수련 3년", "정신건강임상심리사"]},
    "kindergarten_teacher": {"salary_range": "2,200~3,800만원", "career_path": ["유아교육학과 or 아동학과", "보육교사 2급 → 1급 자격", "어린이집·유치원 취업", "원장 자격증 취득 후 개원"]},
    "hr_manager":        {"salary_range": "3,500~7,000만원", "career_path": ["경영·심리·교육학 전공", "채용담당 or 노무팀 입사", "HR 제너럴리스트 경력", "CHRO (최고인사책임자)"]},
    "tax_accountant":    {"salary_range": "4,000~9,000만원 (개업 시 변동)", "career_path": ["세무·회계학 전공", "세무사 시험 합격", "세무법인 or 세무서 근무", "개인 세무 사무소 개업"]},
    "actuary":           {"salary_range": "5,000~1억2천만원", "career_path": ["수학·통계·보험계리학 전공", "계리사 1차→2차 시험 합격", "보험사·연금공단 입사", "선임 계리사 → 계리 부서장"]},
    "webtoon_artist":    {"salary_range": "불규칙 (플랫폼 정산, 상위 작가 수억원)", "career_path": ["그림 실력 독학 or 학원", "단편 웹툰 플랫폼 공모전 도전", "연재 작가 계약", "인기 작품→2차 저작물(드라마·굿즈)"]},
    "vr_ar_developer":   {"salary_range": "4,000~8,000만원", "career_path": ["컴퓨터공학·게임공학 전공", "Unity/Unreal 포트폴리오", "게임사 or XR 스타트업 입사", "시니어 XR 개발자"]},
    "biotech_researcher":{"salary_range": "3,500~7,000만원", "career_path": ["생명공학·화학·의학 전공 (대학원)", "연구소 인턴십", "바이오테크 기업 입사", "연구책임자 or 기술이전 전문가"]},
    "renewable_energy_engineer": {"salary_range": "3,500~7,000만원", "career_path": ["기계·전기·환경공학 전공", "에너지공단·발전사 취업", "태양광·풍력 설계 엔지니어", "신재생에너지 PM"]},
    "urban_planner":     {"salary_range": "3,500~6,500만원", "career_path": ["도시공학·건축·지리학 전공", "국토연구원·LH공사 입사", "도시계획기사 자격증", "도시계획 전문위원"]},
    "flight_attendant":  {"salary_range": "3,000~5,500만원 (항공사별 차이)", "career_path": ["어학능력 준비 (영어 필수)", "항공사 채용 공고 지원", "훈련원 교육 (6~8주)", "국내선 → 국제선 → 사무장"]},
    "game_developer":    {"salary_range": "3,500~7,000만원", "career_path": ["컴퓨터공학·게임공학 전공", "개인 게임 포트폴리오 제작", "게임사 공채 or 인디 개발", "리드 개발자 → 게임 디렉터"]},
}


# ────────────────────────────────────────────────
# 차트 생성 헬퍼
# ────────────────────────────────────────────────

def _make_holland_chart(results: dict) -> str:
    h = results.get("holland", {})
    dims = ["R", "I", "A", "S", "E", "C"]
    vals = [h.get(d, 0.5) * 100 for d in dims]
    labels = ["실용·제작", "탐구·분석", "창작·표현", "사람·돕기", "리더·설득", "체계·관리"]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        line_color="#667eea",
        fillcolor="rgba(102,126,234,0.2)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        margin=dict(l=20, r=20, t=30, b=20),
        height=300,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


def _make_mi_chart(results: dict) -> str:
    mi = results.get("mi", {})
    dims = ["언어", "논리수학", "공간", "음악", "신체운동", "자연탐구", "대인관계", "자기이해"]
    vals = [mi.get(d, 0.5) * 100 for d in dims]
    fig = go.Figure(go.Bar(x=dims, y=vals, marker_color="#667eea"))
    fig.update_layout(
        yaxis_range=[0, 100],
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


def _make_big5_chart(results: dict) -> str:
    b5 = results.get("big5", {})
    dims = ["O", "C", "E", "A", "N"]
    labels = ["개방성", "성실성", "외향성", "친화성", "정서안정"]
    vals = [b5.get(d, 0.5) * 100 for d in dims]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        line_color="#764ba2",
        fillcolor="rgba(118,75,162,0.2)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        margin=dict(l=20, r=20, t=30, b=20),
        height=300,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


def _make_values_chart(results: dict) -> str:
    vl = results.get("values", {})
    dims = list(vl.keys())
    vals = [vl[d] * 100 for d in dims]
    fig = go.Figure(go.Bar(x=dims, y=vals, marker_color="#f59e0b"))
    fig.update_layout(
        yaxis_range=[0, 100],
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


# ────────────────────────────────────────────────
# 공유 URL 생성
# ────────────────────────────────────────────────

def _build_share_url(name: str, holland_code: str, ranked: list) -> str:
    share_data = {
        "n": name,
        "h": holland_code,
        "t": [(r["career_name"], round(r["score"])) for r in ranked[:5]],
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(share_data, ensure_ascii=False).encode()
    ).decode()
    base_url = os.environ.get("APP_URL", "https://jinro-assessment.onrender.com")
    return f"{base_url}/?r={encoded}"


def _decode_share_param(param: str) -> dict | None:
    try:
        decoded = base64.urlsafe_b64decode(param.encode()).decode()
        return json.loads(decoded)
    except Exception:
        return None


# ────────────────────────────────────────────────
# HTML 보고서 생성
# ────────────────────────────────────────────────

def _generate_html_report(name: str, age_group: str, holland_code: str,
                           results: dict, ranked: list) -> str:
    age_label = {"child": "아동", "teen": "청소년", "young_adult": "청년", "adult": "성인"}.get(age_group, "")

    top_careers_html = ""
    for i, fit in enumerate(ranked[:8]):
        c = fit["career_data"]
        diff = c.get("difficulty", "보통")
        diff_color = {
            "낮음": "#22c55e",
            "보통": "#3b82f6",
            "높음": "#f59e0b",
            "매우 높음": "#ef4444",
        }.get(diff, "#888")
        reasons_html = "".join(
            f"<li><b>[{r['theory']}]</b> {r['detail']}</li>"
            for r in fit.get("top_reasons", [])[:3]
        )
        detail = CAREER_DETAIL_DB.get(c["id"], {})
        salary_str = detail.get("salary_range", c.get("salary_level", ""))
        top_careers_html += f"""
        <div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:1.1rem;font-weight:700;">{i+1}. {c['name']}</span>
                <span style="background:#667eea;color:white;padding:3px 10px;border-radius:20px;font-size:0.9rem;">{fit['score']:.0f}점</span>
            </div>
            <div style="color:#555;font-size:0.9rem;margin:6px 0;">{c['description']}</div>
            <div style="font-size:0.85rem;">
                <b>학력:</b> {c['education']} &nbsp;|&nbsp;
                <b>예상 연봉:</b> {salary_str} &nbsp;|&nbsp;
                <b>성장성:</b> {c['job_growth']} &nbsp;|&nbsp;
                <b style="color:{diff_color}">난이도: {diff}</b>
            </div>
            <ul style="font-size:0.85rem;margin:6px 0 0 0;">{reasons_html}</ul>
        </div>"""

    holland_html = ""
    if "holland" in results:
        for k, v in results["holland"].items():
            pct = int(v * 100)
            holland_html += f"""
            <div style="margin-bottom:6px;">
                <span style="display:inline-block;width:80px;">{k}</span>
                <div style="display:inline-block;background:#e5e7eb;width:200px;height:12px;border-radius:6px;vertical-align:middle;">
                    <div style="background:#667eea;width:{pct * 2}px;height:12px;border-radius:6px;"></div>
                </div>
                <span style="margin-left:8px;font-size:0.85rem;">{pct}</span>
            </div>"""

    now_str = pd.Timestamp.now().strftime("%Y년 %m월 %d일")
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{name}님 진로 탐색 결과</title>
<style>
  body {{ font-family: 'Malgun Gothic', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a2e; }}
  h1 {{ background: linear-gradient(135deg,#667eea,#764ba2); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .meta {{ background:#f8f9ff; border-radius:10px; padding:14px; margin-bottom:20px; }}
  @media print {{ body {{ margin:20px; }} }}
</style>
</head>
<body>
<h1>진로 탐색 결과 보고서</h1>
<div class="meta">
  <b>이름:</b> {name} &nbsp;&nbsp; <b>연령대:</b> {age_label} &nbsp;&nbsp; <b>흥미 코드:</b> {holland_code}
  <br><small style="color:#888;">본 결과는 다중이론 앙상블(MTECA) 기반 진로 탐색 프로그램이 생성한 참고 자료입니다.</small>
</div>

<h2 style="margin-bottom:10px;">추천 직업 상위 8개</h2>
{top_careers_html}

<h2 style="margin-bottom:10px;">흥미 유형 프로파일</h2>
<div style="padding:10px;">{holland_html}</div>

<p style="color:#999;font-size:0.8rem;margin-top:30px;border-top:1px solid #eee;padding-top:10px;">
생성일: {now_str} | 진로 탐색 시스템 (jinro-assessment.onrender.com)
</p>
</body></html>"""
    return html


# ────────────────────────────────────────────────
# 세션 plan 직렬화 헬퍼
# ────────────────────────────────────────────────

def _plan_to_session(plan: dict) -> dict:
    """get_assessment_plan 결과를 JSON 직렬화 가능한 형태로 변환."""
    sections = []
    for sec in plan.get("sections", []):
        questions = []
        for q in sec.get("questions", []):
            entry = {"id": q["id"], "dim": q["dim"]}
            if "reverse" in q:
                entry["reverse"] = q["reverse"]
            questions.append(entry)
        sections.append({
            "key": sec["key"],
            "title": sec["title"],
            "desc": sec.get("desc", ""),
            "questions": questions,
        })
    return {
        "label": plan.get("label", ""),
        "sections": sections,
        "weights": plan.get("weights", {}),
        "use_anchors": plan.get("use_anchors", False),
        "use_big5": plan.get("use_big5", False),
    }


def _build_profile_html(results: dict) -> str:
    """간단한 프로파일 HTML 생성 (나의 프로파일 탭)"""
    html = ""
    h = results.get("holland", {})
    mi = results.get("mi", {})
    vl = results.get("values", {})

    if h:
        h_labels = {"R":"실용·제작","I":"탐구·분석","A":"창작·표현","S":"사람·돕기","E":"리더·설득","C":"체계·관리"}
        top_h = sorted(h.keys(), key=lambda k: h[k], reverse=True)[:3]
        html += "<h4 style='margin-bottom:0.5rem;'>좋아하는 활동 유형 (Holland)</h4>"
        for k in top_h:
            pct = int(h[k]*100)
            html += f"<div style='margin-bottom:0.4rem;'><span style='display:inline-block;width:100px;font-weight:600;'>{h_labels.get(k,k)}</span>"
            html += f"<div style='display:inline-block;background:#e8e8e8;width:200px;height:10px;border-radius:5px;vertical-align:middle;'>"
            html += f"<div style='background:#667eea;width:{pct*2}px;height:10px;border-radius:5px;'></div></div>"
            html += f"<span style='margin-left:8px;font-size:0.85rem;'>{pct}</span></div>"

    if mi:
        top_mi = sorted(mi.keys(), key=lambda k: mi[k], reverse=True)[:3]
        html += "<hr style='margin:1rem 0;'><h4 style='margin-bottom:0.5rem;'>잘하는 능력 영역 (다중지능)</h4>"
        for k in top_mi:
            pct = int(mi[k]*100)
            html += f"<div style='margin-bottom:0.4rem;'><span style='display:inline-block;width:100px;font-weight:600;'>{k}</span>"
            html += f"<div style='display:inline-block;background:#e8e8e8;width:200px;height:10px;border-radius:5px;vertical-align:middle;'>"
            html += f"<div style='background:#764ba2;width:{pct*2}px;height:10px;border-radius:5px;'></div></div>"
            html += f"<span style='margin-left:8px;font-size:0.85rem;'>{pct}</span></div>"

    if vl:
        top_v = sorted(vl.keys(), key=lambda k: vl[k], reverse=True)[:3]
        html += "<hr style='margin:1rem 0;'><h4 style='margin-bottom:0.5rem;'>일에서 중요하게 여기는 가치</h4>"
        values_meaning = {
            "능력발휘":"내 능력을 최대한 쓸 수 있는 일","자율성":"스스로 결정하고 자유롭게 일하기",
            "보수":"경제적 보상이 중요한 동기","안정성":"오래 안정적으로 일하는 환경",
            "사회적인정":"사회에서 인정받는 일","사회봉사":"다른 사람에게 도움이 되는 일",
            "자기계발":"계속 배우고 성장하는 일","창의성":"창의적으로 새로운 것을 만드는 일",
            "대인관계":"좋은 사람들과 함께 일하기",
        }
        for i, k in enumerate(top_v, 1):
            html += f"<div style='background:#f8f9ff;border-radius:8px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;border-left:3px solid #f59e0b;'>"
            html += f"<span style='font-weight:800;color:#f59e0b;'>{i}순위</span> <strong>{k}</strong> — {values_meaning.get(k, k)}</div>"

    return html or "<p style='color:#888;'>프로파일 데이터가 없습니다.</p>"


def _compute_holland_code(holland_scores: dict) -> str:
    if not holland_scores:
        return "---"
    sorted_dims = sorted(holland_scores.items(), key=lambda x: x[1], reverse=True)
    return "".join(d for d, _ in sorted_dims[:3])


def _canonical_url(path: str) -> str:
    return f"{APP_URL}{path}"


def _career_lookup(career_id: str) -> dict | None:
    for career in CAREERS_DB:
        if career.get("id") == career_id:
            return career
    return None


def _career_display(career: dict, lang: str) -> dict:
    cid = career.get("id", "")
    detail = CAREER_DETAIL_DB.get(cid, {})
    global_data = CAREER_GLOBAL_DATA.get(cid, {})
    name = tc(cid, lang) if lang != "ko" else career.get("name", cid)
    desc = CAREER_DESC_EN.get(cid) if lang != "ko" else None
    return {
        **career,
        "display_name": name,
        "display_description": desc or career.get("description", ""),
        "salary_display": global_data.get("salary_global") if lang != "ko" else detail.get("salary_range"),
        "roadmap_display": global_data.get("roadmap") if lang != "ko" else detail.get("career_path", []),
    }


def _related_careers(career: dict, limit: int = 6) -> list[dict]:
    category = career.get("category")
    current_id = career.get("id")
    related = [c for c in CAREERS_DB if c.get("category") == category and c.get("id") != current_id]
    return related[:limit]


def _related_tests_for_career(career: dict, limit: int = 4) -> list[tuple[str, dict]]:
    cid = career.get("id", "")
    category = career.get("category", "")
    slugs = ["job-aptitude-test", "personality-career-test", "career-values-test"]
    if any(term in category for term in ("IT", "개발", "공학", "기술", "이공계", "과학", "연구")) or any(term in cid for term in ("developer", "engineer", "data", "ai", "cyber")):
        slugs = ["developer-aptitude-test", "stem-career-test", "remote-work-career-test", "job-aptitude-test"]
    elif any(term in category for term in ("의료", "보건")) or any(term in cid for term in ("nurse", "doctor", "therapist", "medical")):
        slugs = ["healthcare-career-test", "nurse-aptitude-test", "career-values-test", "job-aptitude-test"]
    elif "교육" in category or "teacher" in cid:
        slugs = ["teacher-aptitude-test", "personality-career-test", "career-values-test", "job-aptitude-test"]
    elif any(term in category for term in ("예술", "문화", "미디어", "창작")) or any(term in cid for term in ("designer", "artist", "writer", "music")):
        slugs = ["creative-career-test", "designer-aptitude-test", "personality-career-test", "career-values-test"]
    elif any(term in category for term in ("경영", "금융", "기업")):
        slugs = ["business-career-test", "job-aptitude-test", "career-values-test", "career-change-test"]
    return [(slug, SEO_TEST_PAGES[slug]) for slug in slugs if slug in SEO_TEST_PAGES][:limit]


def _test_seo_detail(slug: str, page: dict) -> dict:
    fallback = {
        "primary_keyword": page["title"].lower(),
        "search_title": page["title"],
        "intent": page["description"],
        "best_for": ["People comparing career options", "Students and adults planning next steps", "Users who want a practical career match"],
        "compare": ["Job Aptitude Test", "Personality Career Test", "Career Values Test"],
    }
    return {**fallback, **SEO_TEST_DETAILS.get(slug, {})}


def _guide_related_careers(guide: dict, lang: str) -> list[dict]:
    by_id = {career.get("id"): career for career in CAREERS_DB}
    selected = []
    for cid in guide.get("related_careers", []):
        career = by_id.get(cid)
        if career:
            selected.append(_career_display(career, lang))
    return selected


def _guide_related_tests(guide: dict) -> list[tuple[str, dict]]:
    return [
        (slug, SEO_TEST_PAGES[slug])
        for slug in guide.get("related_tests", [])
        if slug in SEO_TEST_PAGES
    ]


def _guide_faq(guide: dict) -> list[dict]:
    keyword = guide.get("keyword", "career test")
    return [
        {
            "q": f"How should I use this guide for {keyword}?",
            "a": "Use it to create a shortlist of careers, then compare daily work, preparation, values, and related paths before making a decision.",
        },
        {
            "q": "Can a career test choose the right career for me?",
            "a": "No. A career test is a sorting and reflection tool. It can highlight promising options, but you still need research and small real-world experiments.",
        },
        {
            "q": "What is the next step after reading this guide?",
            "a": "Take a relevant career test, read several career profiles, and choose one small action such as a course, project, interview, or shadowing experience.",
        },
    ]


def _top_dims(score_map: dict, limit: int = 3) -> list[tuple[str, float]]:
    return sorted(score_map.items(), key=lambda item: item[1], reverse=True)[:limit]


def _career_article_sections(career: dict, lang: str) -> dict:
    name = tc(career.get("id", ""), lang) if lang != "ko" else career.get("name", "this career")
    category = tcat(career.get("category", ""), lang)
    holland = _top_dims(career.get("holland", {}), 3)
    values = _top_dims(career.get("values", {}), 3)
    big5 = _top_dims(career.get("big5", {}), 2)
    majors = career.get("related_majors", [])[:4]

    interest_labels = {
        "R": "hands-on work",
        "I": "analysis and research",
        "A": "creative expression",
        "S": "helping and teaching",
        "E": "leading and persuading",
        "C": "organizing and detail work",
    }
    top_interest = ", ".join(interest_labels.get(dim, dim) for dim, _ in holland) or "mixed work styles"
    top_values = ", ".join(str(dim) for dim, _ in values) or "personal work values"
    top_traits = ", ".join(str(dim) for dim, _ in big5) or "work habits"
    major_text = ", ".join(majors) if majors else "related courses, projects, and entry-level experience"

    return {
        "daily_work": [
            f"People in {name} usually spend time solving problems inside the {category} field.",
            f"The work often rewards {top_interest}, especially when paired with steady learning and feedback.",
            "Actual tasks vary by country, employer, seniority, and whether the role is in a large organization or a smaller team.",
        ],
        "fit_signs": [
            f"You may want to explore this path if you enjoy {top_interest}.",
            f"This profile also emphasizes values such as {top_values}.",
            f"Personality fit is not fixed, but this career profile tends to reward habits related to {top_traits}.",
        ],
        "starter_steps": [
            f"Review courses or majors connected to {major_text}.",
            "Interview someone in the field and ask what their week actually looks like.",
            "Try a small project, shadowing experience, volunteer role, internship, or beginner portfolio piece before committing deeply.",
        ],
        "watch_out": [
            "Do not choose a career only because the match score is high.",
            "Check current salary, licensing, hiring demand, and local education requirements before making important decisions.",
            "Compare this path with at least three related careers so you can see whether the attraction is the field, the work style, or a specific job title.",
        ],
    }


def _top_career_sample(limit: int = 12) -> list[dict]:
    priority_ids = [
        "software_dev", "data_scientist", "ai_engineer", "nurse",
        "teacher", "ux_designer", "financial_analyst", "counselor",
        "doctor", "marketing_manager", "game_developer", "architect",
    ]
    by_id = {c.get("id"): c for c in CAREERS_DB}
    selected = [by_id[cid] for cid in priority_ids if cid in by_id]
    for career in CAREERS_DB:
        if len(selected) >= limit:
            break
        if career not in selected:
            selected.append(career)
    return selected[:limit]


def _analytics_conn():
    os.makedirs(os.path.dirname(ANALYTICS_DB), exist_ok=True)
    conn = sqlite3.connect(ANALYTICS_DB, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            event_name TEXT NOT NULL,
            visitor_id TEXT,
            page_path TEXT,
            page_type TEXT,
            target_path TEXT,
            section_key TEXT,
            section_index INTEGER,
            percent INTEGER,
            seconds INTEGER,
            params_json TEXT,
            referrer TEXT,
            user_agent TEXT,
            ip_hash TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_created ON analytics_events(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics_events(event_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_page ON analytics_events(page_path)")
    return conn


def _safe_int(value):
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _hash_ip(ip: str) -> str:
    salt = app.secret_key or "careersdna"
    return hashlib.sha256(f"{salt}:{ip or ''}".encode("utf-8")).hexdigest()[:24]


def _store_analytics_event(payload: dict) -> None:
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    event_name = str(payload.get("event") or "")[:80]
    if not event_name:
        return
    page_path = str(params.get("page_path") or payload.get("page_path") or request.path)[:300]
    page_type = str(params.get("page_type") or params.get("type") or "")[:80]
    target_path = str(params.get("target_path") or "")[:300]
    section_key = str(params.get("section_key") or "")[:120]
    visitor_id = str(payload.get("visitor_id") or "")[:80]
    user_agent = (request.headers.get("User-Agent") or "")[:300]
    referrer = (request.headers.get("Referer") or "")[:300]
    ip_hash = _hash_ip(request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip())

    conn = _analytics_conn()
    try:
        conn.execute(
            """
            INSERT INTO analytics_events (
                created_at, event_name, visitor_id, page_path, page_type, target_path,
                section_key, section_index, percent, seconds, params_json,
                referrer, user_agent, ip_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(timespec="seconds"),
                event_name,
                visitor_id,
                page_path,
                page_type,
                target_path,
                section_key,
                _safe_int(params.get("section_index")),
                _safe_int(params.get("percent")),
                _safe_int(params.get("seconds")),
                json.dumps(params, ensure_ascii=False)[:2000],
                referrer,
                user_agent,
                ip_hash,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _fetch_all(query: str, args: tuple = ()) -> list[dict]:
    conn = _analytics_conn()
    try:
        rows = conn.execute(query, args).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _fetch_one(query: str, args: tuple = ()) -> dict:
    rows = _fetch_all(query, args)
    return rows[0] if rows else {}


def _analytics_summary(days: int = 7) -> dict:
    since = datetime.utcnow().timestamp() - days * 86400
    since_iso = datetime.utcfromtimestamp(since).isoformat(timespec="seconds")
    args = (since_iso,)
    visible_filter = "created_at >= ? AND page_path NOT LIKE '/admin%' AND page_path != '/probe'"
    overview = _fetch_one(
        f"""
        SELECT
          COUNT(*) AS events,
          COUNT(DISTINCT visitor_id) AS visitors,
          SUM(CASE WHEN event_name='page_view_custom' THEN 1 ELSE 0 END) AS pageviews,
          SUM(CASE WHEN event_name='view_result' THEN 1 ELSE 0 END) AS results
        FROM analytics_events
        WHERE {visible_filter}
        """,
        args,
    )
    starts = _fetch_one(
        f"""
        SELECT COUNT(*) AS starts
        FROM analytics_events
        WHERE {visible_filter} AND event_name IN (
          'start_assessment','click_start_from_home','click_start_from_landing',
          'click_start_from_career','click_start_from_careers_index'
        )
        """,
        args,
    )
    top_pages = _fetch_all(
        f"""
        SELECT page_path, page_type, COUNT(*) AS views
        FROM analytics_events
        WHERE {visible_filter} AND event_name='page_view_custom'
        GROUP BY page_path, page_type
        ORDER BY views DESC
        LIMIT 20
        """,
        args,
    )
    liked_pages = _fetch_all(
        f"""
        SELECT page_path,
          SUM(CASE WHEN event_name='engaged_time' AND seconds >= 45 THEN 1 ELSE 0 END) AS long_reads,
          SUM(CASE WHEN event_name='scroll_depth' AND percent >= 75 THEN 1 ELSE 0 END) AS deep_scrolls,
          SUM(CASE WHEN event_name LIKE 'click_start_%' THEN 1 ELSE 0 END) AS starts,
          SUM(CASE WHEN event_name='feedback_useful' THEN 1 ELSE 0 END) AS useful,
          COUNT(*) AS signals
        FROM analytics_events
        WHERE {visible_filter}
        GROUP BY page_path
        HAVING long_reads > 0 OR deep_scrolls > 0 OR starts > 0 OR useful > 0
        ORDER BY (long_reads * 3 + deep_scrolls * 2 + starts * 4 + useful * 5) DESC
        LIMIT 15
        """,
        args,
    )
    weak_pages = _fetch_all(
        """
        SELECT v.page_path, COUNT(*) AS views,
          COALESCE(e.engaged, 0) AS engaged,
          ROUND((COUNT(*) - COALESCE(e.engaged, 0)) * 100.0 / COUNT(*), 1) AS weak_rate
        FROM analytics_events v
        LEFT JOIN (
          SELECT page_path, COUNT(*) AS engaged
          FROM analytics_events
          WHERE created_at >= ? AND page_path NOT LIKE '/admin%' AND page_path != '/probe' AND (
            (event_name='engaged_time' AND seconds >= 45)
            OR (event_name='scroll_depth' AND percent >= 75)
            OR event_name LIKE 'click_start_%'
            OR event_name='feedback_useful'
          )
          GROUP BY page_path
        ) e ON e.page_path = v.page_path
        WHERE v.created_at >= ? AND v.page_path NOT LIKE '/admin%' AND v.page_path != '/probe' AND v.event_name='page_view_custom'
        GROUP BY v.page_path
        HAVING views >= 3
        ORDER BY weak_rate DESC, views DESC
        LIMIT 15
        """,
        (since_iso, since_iso),
    )
    survey_dropoff = _fetch_all(
        """
        SELECT
          COALESCE(v.section_key, c.section_key, x.section_key) AS section_key,
          COALESCE(v.section_index, c.section_index, x.section_index) AS section_index,
          COALESCE(v.views, 0) AS views,
          COALESCE(c.completes, 0) AS completes,
          COALESCE(x.exits, 0) AS exits,
          CASE WHEN COALESCE(v.views, 0) = 0 THEN 0
               ELSE ROUND((COALESCE(v.views, 0) - COALESCE(c.completes, 0)) * 100.0 / COALESCE(v.views, 1), 1)
          END AS drop_rate
        FROM (
          SELECT section_key, section_index, COUNT(*) AS views
          FROM analytics_events
          WHERE created_at >= ? AND page_path NOT LIKE '/admin%' AND event_name='view_survey_section'
          GROUP BY section_key, section_index
        ) v
        LEFT JOIN (
          SELECT section_key, section_index, COUNT(*) AS completes
          FROM analytics_events
          WHERE created_at >= ? AND page_path NOT LIKE '/admin%' AND event_name='complete_section'
          GROUP BY section_key, section_index
        ) c ON c.section_key = v.section_key AND c.section_index = v.section_index
        LEFT JOIN (
          SELECT section_key, section_index, COUNT(*) AS exits
          FROM analytics_events
          WHERE created_at >= ? AND page_path NOT LIKE '/admin%' AND event_name='survey_section_exit'
          GROUP BY section_key, section_index
        ) x ON x.section_key = v.section_key AND x.section_index = v.section_index
        ORDER BY section_index ASC
        """,
        (since_iso, since_iso, since_iso),
    )
    top_clicks = _fetch_all(
        f"""
        SELECT event_name, target_path, COUNT(*) AS clicks
        FROM analytics_events
        WHERE {visible_filter} AND event_name LIKE 'click_%'
        GROUP BY event_name, target_path
        ORDER BY clicks DESC
        LIMIT 20
        """,
        args,
    )
    referrers = _fetch_all(
        f"""
        SELECT referrer, COUNT(*) AS visits
        FROM analytics_events
        WHERE {visible_filter} AND event_name='page_view_custom' AND referrer != ''
        GROUP BY referrer
        ORDER BY visits DESC
        LIMIT 15
        """,
        args,
    )
    feedback = _fetch_all(
        f"""
        SELECT page_path,
          SUM(CASE WHEN event_name='feedback_useful' THEN 1 ELSE 0 END) AS useful,
          SUM(CASE WHEN event_name='feedback_not_useful' THEN 1 ELSE 0 END) AS not_useful,
          COUNT(*) AS total
        FROM analytics_events
        WHERE {visible_filter} AND event_name IN ('feedback_useful', 'feedback_not_useful')
        GROUP BY page_path
        ORDER BY total DESC, useful DESC
        LIMIT 20
        """,
        args,
    )
    return {
        "days": days,
        "overview": overview,
        "starts": starts.get("starts", 0),
        "top_pages": top_pages,
        "liked_pages": liked_pages,
        "weak_pages": weak_pages,
        "survey_dropoff": survey_dropoff,
        "top_clicks": top_clicks,
        "referrers": referrers,
        "feedback": feedback,
    }


def _analytics_allowed() -> bool:
    token = os.environ.get("ANALYTICS_TOKEN", "")
    if request.remote_addr in ("127.0.0.1", "::1", "localhost"):
        return True
    if token and request.args.get("token") == token:
        session["analytics_allowed"] = True
        return True
    return bool(token and session.get("analytics_allowed"))


def _test_faq(page: dict) -> list[dict]:
    return [
        {
            "q": f"Who is the {page['title']} for?",
            "a": f"It is for people who want to compare career options using interests, strengths, personality, and work values. The page is especially relevant for the {page['age_hint']} age range.",
        },
        {
            "q": "Does the test guarantee the right career?",
            "a": "No. The result is an exploration tool. It shows career paths worth researching, not a guarantee of income, admission, hiring, or long-term satisfaction.",
        },
        {
            "q": "How should I use the result?",
            "a": "Use the result to compare several careers, read career profiles, ask better questions, and plan small experiments such as courses, interviews, projects, or internships.",
        },
    ]


def _career_faq(career: dict, display: dict) -> list[dict]:
    name = display.get("display_name", career.get("name", "this career"))
    return [
        {
            "q": f"How do I know if {name} fits me?",
            "a": f"Compare the daily work with your interests, strengths, personality, and values. This page gives a profile overview, and the full assessment compares {name} with other career options.",
        },
        {
            "q": f"What should I check before choosing {name}?",
            "a": "Check current education requirements, hiring demand, salary ranges, licensing rules, and local entry paths. Career data can vary by country, region, and employer.",
        },
        {
            "q": f"What are related paths to {name}?",
            "a": "Look at related careers in the same field and compare work style, preparation difficulty, and long-term growth before committing.",
        },
    ]


# ────────────────────────────────────────────────
# 라우트
# ────────────────────────────────────────────────

def _tool_category(slug: str, tool: dict) -> str:
    tool_type = tool.get("type", "")
    if slug.startswith("pdf-"):
        return "pdf"
    if tool_type in {
        "json_formatter", "base64_converter", "url_encoder", "hash_generator",
        "timestamp_converter", "regex_tester", "uuid_generator", "jwt_decoder",
        "csv_to_json", "xml_formatter", "html_formatter", "sql_formatter",
        "color_converter", "meta_tag_previewer", "robots_txt_generator",
    }:
        return "developer"
    if tool_type in {"image_resizer", "image_compressor", "image_to_webp"}:
        return "image"
    if tool_type in {"qr_code_generator", "invoice_generator"}:
        return "business"
    if tool_type in {
        "word_counter", "case_converter", "text_repeater", "text_diff",
        "markdown_previewer", "lorem_ipsum_generator", "keyword_density_checker",
    }:
        return "text"
    if tool_type in {
        "percentage_calculator", "age_calculator", "time_calculator",
        "tip_calculator", "unit_converter",
    }:
        return "calculator"
    return "productivity"


def _tools_by_category() -> dict[str, dict[str, dict]]:
    grouped = {slug: {} for slug in TOOL_CATEGORIES}
    for slug, tool in DAILY_TOOLS.items():
        grouped.setdefault(_tool_category(slug, tool), {})[slug] = tool
    return grouped


def _tool_related(slug: str, limit: int = 12) -> dict[str, dict]:
    tool = DAILY_TOOLS.get(slug, {})
    category = _tool_category(slug, tool)
    grouped = _tools_by_category()
    related: dict[str, dict] = {}
    for item_slug, item in grouped.get(category, {}).items():
        if item_slug != slug:
            related[item_slug] = item
        if len(related) >= limit:
            return related
    for item_slug, item in DAILY_TOOLS.items():
        if item_slug != slug and item_slug not in related:
            related[item_slug] = item
        if len(related) >= limit:
            break
    return related


def _tool_seo_content(slug: str, tool: dict) -> dict:
    keyword = tool.get("keyword", tool.get("title", "online tool"))
    title = tool.get("title", keyword)
    tool_type = tool.get("type", "")
    category = _tool_category(slug, tool)
    category_title = TOOL_CATEGORIES.get(category, {}).get("title", "Online Tools")
    local_note = (
        "This tool runs in your browser. For file-based tools, the selected file is processed locally in the tab instead of being uploaded to this server."
        if slug.startswith("pdf-") or category == "image"
        else "This tool is designed for quick browser use without creating an account or sending a form to a separate service."
    )
    use_cases = {
        "developer": [
            f"Clean up copied data before pasting it into a code editor or API client.",
            f"Check small snippets while debugging without opening a full development environment.",
            f"Prepare readable examples for documentation, tickets, pull requests, and notes.",
        ],
        "text": [
            f"Review drafts before publishing a blog post, landing page, email, or documentation.",
            f"Prepare text for social posts, product pages, classroom materials, and quick copy edits.",
            f"Check repeated wording, formatting, or simple content patterns before sharing.",
        ],
        "pdf": [
            f"Make small PDF changes when you need a quick document cleanup.",
            f"Prepare pages for forms, school work, business documents, and personal archives.",
            f"Handle simple page-level PDF tasks without installing a desktop editor.",
        ],
        "image": [
            f"Prepare images for websites, profiles, documents, marketplaces, and email attachments.",
            f"Reduce file size before upload limits or improve image dimensions for a layout.",
            f"Create web-friendly image versions for faster pages and smaller downloads.",
        ],
        "business": [
            f"Create simple assets for clients, invoices, events, menus, and small business workflows.",
            f"Prepare quick business documents without setting up a full design or accounting tool.",
            f"Use repeatable templates for everyday operational tasks.",
        ],
        "calculator": [
            f"Solve common number questions while shopping, planning, scheduling, or budgeting.",
            f"Check small calculations without opening a spreadsheet.",
            f"Compare values quickly before making a decision.",
        ],
        "productivity": [
            f"Use a small focused tool for a task that does not need a full app.",
            f"Support studying, planning, prioritizing, and repeatable daily routines.",
            f"Keep a lightweight workflow open in a browser tab.",
        ],
    }.get(category, [])
    tips = [
        f"Paste or enter only the content needed for the {keyword}.",
        "Check the result before using it in production, publishing, or sending it to someone else.",
        f"Bookmark this page if you use this {category_title.lower()} task regularly.",
    ]
    if tool_type in {"jwt_decoder", "hash_generator", "password_generator"}:
        tips[0] = "Avoid pasting live secrets, production credentials, private keys, or sensitive tokens."
    if tool_type in {"robots_txt_generator", "meta_tag_previewer", "keyword_density_checker"}:
        tips.append("Use the output as a review aid, not as a guarantee of search ranking or indexing.")
    return {
        "summary": f"{title} is a free browser-based {keyword} for quick everyday use. It focuses on a narrow task so you can open the page, finish the job, and move on without account setup.",
        "local_note": local_note,
        "use_cases": use_cases,
        "tips": tips,
        "faq": [
            {
                "q": f"Is this {keyword} free?",
                "a": f"Yes. You can use this {keyword} page without creating an account.",
            },
            {
                "q": "Do I need to install anything?",
                "a": "No. The tool runs in a modern web browser.",
            },
            {
                "q": "Can I use it on mobile?",
                "a": "Yes. The page is responsive, although larger files or long text are usually easier to handle on a desktop screen.",
            },
        ],
    }


def _blog_related_tools(post: dict) -> dict[str, dict]:
    related: dict[str, dict] = {}
    for slug in post.get("related_tools", []):
        if slug in DAILY_TOOLS:
            related[slug] = DAILY_TOOLS[slug]
    return related


@app.route("/")
def index():
    lang = session.get("lang", DEFAULT_LANG)
    r_param = request.args.get("r")
    if r_param:
        shared_data = _decode_share_param(r_param)
        if shared_data:
            return render_template(
                "welcome.html",
                lang=lang,
                LANG_CONFIG=LANG_CONFIG,
                shared_data=shared_data,
                test_pages=SEO_TEST_PAGES,
                guide_pages=SEO_GUIDE_PAGES,
                featured_careers=[_career_display(c, lang) for c in _top_career_sample(8)],
                meta_title="Shared Career Result | Career Assessment",
                meta_description="View a shared career exploration result and take the free career assessment.",
                canonical_url=_canonical_url("/"),
            )
    return render_template(
        "tools_index.html",
        lang=lang,
        tools=DAILY_TOOLS,
        categories=TOOL_CATEGORIES,
        grouped_tools=_tools_by_category(),
        blog_posts=_published_blog_posts(),
        meta_title="Free Online Tools | PDF, Image, Text, Developer, and Calculator Utilities",
        meta_description="Free browser tools for PDFs, images, text, code, calculators, productivity, business tasks, and career exploration.",
        canonical_url=_canonical_url("/"),
    )


@app.route("/tests/<slug>")
def seo_test_page(slug):
    page = SEO_TEST_PAGES.get(slug)
    if not page:
        return redirect(url_for("index"))
    lang = session.get("lang", DEFAULT_LANG)
    seo_detail = _test_seo_detail(slug, page)
    related_tests = {k: v for k, v in SEO_TEST_PAGES.items() if k != slug}
    related_tests = dict(list(related_tests.items())[:8])
    return render_template(
        "seo_test.html",
        lang=lang,
        page=page,
        seo_detail=seo_detail,
        faq=_test_faq(page),
        slug=slug,
        related_tests=related_tests,
        featured_careers=[_career_display(c, lang) for c in _top_career_sample(6)],
        meta_title=f"{seo_detail['search_title']} | Career Aptitude Test",
        meta_description=f"{seo_detail['intent']} Free assessment with 174 career profiles and practical comparison points.",
        canonical_url=_canonical_url(f"/tests/{slug}"),
    )


@app.route("/guides/<slug>")
def seo_guide_page(slug):
    guide = SEO_GUIDE_PAGES.get(slug)
    if not guide:
        return redirect(url_for("index"))
    lang = session.get("lang", DEFAULT_LANG)
    return render_template(
        "seo_guide.html",
        lang=lang,
        slug=slug,
        guide=guide,
        faq=_guide_faq(guide),
        related_tests=_guide_related_tests(guide),
        related_careers=_guide_related_careers(guide, lang),
        meta_title=f"{guide['title']} | Free Career Test",
        meta_description=guide["description"],
        canonical_url=_canonical_url(f"/guides/{slug}"),
    )


@app.route("/tools")
def tools_index():
    return redirect(url_for("index"))


@app.route("/pdf-tools")
def pdf_tools_index():
    return redirect(url_for("tool_category_page", category_slug="pdf"))


@app.route("/tools/category/<category_slug>")
def tool_category_page(category_slug):
    category = TOOL_CATEGORIES.get(category_slug)
    if not category:
        return redirect(url_for("tools_index"))
    lang = session.get("lang", DEFAULT_LANG)
    tools = _tools_by_category().get(category_slug, {})
    return render_template(
        "tools_category.html",
        lang=lang,
        category_slug=category_slug,
        category=category,
        tools=tools,
        categories=TOOL_CATEGORIES,
        meta_title=f"{category['title']} | Free Online Tools",
        meta_description=category["description"],
        canonical_url=_canonical_url(f"/tools/category/{category_slug}"),
    )


@app.route("/tools/<slug>")
def tool_page(slug):
    tool = DAILY_TOOLS.get(slug)
    if not tool:
        return redirect(url_for("tools_index"))
    lang = session.get("lang", DEFAULT_LANG)
    return render_template(
        "tool_page.html",
        lang=lang,
        slug=slug,
        tool=tool,
        tool_content=_tool_seo_content(slug, tool),
        related_tools=_tool_related(slug),
        meta_title=f"{tool['title']} | Free Browser Utility",
        meta_description=tool["description"],
        canonical_url=_canonical_url(f"/tools/{slug}"),
    )


@app.route("/blog")
def blog_index():
    lang = session.get("lang", DEFAULT_LANG)
    return render_template(
        "blog_index.html",
        lang=lang,
        posts=_published_blog_posts(),
        meta_title="Utility Guides | PDF, Image, Text, and Developer Tool Tutorials",
        meta_description="Practical guides for using free browser tools for PDFs, images, text, developer workflows, and everyday work tasks.",
        canonical_url=_canonical_url("/blog"),
    )


@app.route("/blog/<slug>")
def blog_post(slug):
    post = BLOG_POSTS.get(slug)
    if not post or not _is_blog_published(post):
        return redirect(url_for("blog_index"))
    lang = session.get("lang", DEFAULT_LANG)
    tool = DAILY_TOOLS.get(post.get("tool_slug", ""))
    return render_template(
        "blog_post.html",
        lang=lang,
        slug=slug,
        post=post,
        tool=tool,
        related_tools=_blog_related_tools(post),
        meta_title=f"{post['title']} | Utility Guide",
        meta_description=post["description"],
        canonical_url=_canonical_url(f"/blog/{slug}"),
    )


@app.route("/careers")
def careers_index():
    lang = session.get("lang", DEFAULT_LANG)
    grouped = get_careers_by_category()
    display_grouped = {
        category: [_career_display(c, lang) for c in careers]
        for category, careers in grouped.items()
    }
    return render_template(
        "careers.html",
        lang=lang,
        grouped=display_grouped,
        total_careers=len(CAREERS_DB),
        meta_title="Career Library | 174 Career Profiles",
        meta_description="Browse 174 career profiles and compare education, growth, work style, and related majors before taking the career test.",
        canonical_url=_canonical_url("/careers"),
    )


@app.route("/career/<career_id>")
def career_detail(career_id):
    lang = session.get("lang", DEFAULT_LANG)
    career = _career_lookup(career_id)
    if not career:
        return redirect(url_for("careers_index"))
    display = _career_display(career, lang)
    related = [_career_display(c, lang) for c in _related_careers(career)]
    review = CAREER_REVIEWS.get(career_id, {}).get(lang) or CAREER_REVIEWS.get(career_id, {}).get("en")
    article = _career_article_sections(career, lang)
    faq = _career_faq(career, display)
    related_tests = _related_tests_for_career(career)
    return render_template(
        "career_detail.html",
        lang=lang,
        career=display,
        related=related,
        related_tests=related_tests,
        review=review,
        article=article,
        faq=faq,
        meta_title=f"{display['display_name']} Career Test and Fit Guide",
        meta_description=f"Explore {display['display_name']} career fit, daily work, education, salary signals, related paths, and tests to compare this career with your strengths.",
        canonical_url=_canonical_url(f"/career/{career_id}"),
    )


@app.route("/privacy")
def privacy():
    lang = session.get("lang", DEFAULT_LANG)
    return render_template(
        "privacy.html",
        lang=lang,
        meta_title="Privacy Policy | Career Assessment",
        meta_description="Privacy policy for Career Assessment, including cookies, analytics, advertising, and assessment data handling.",
        canonical_url=_canonical_url("/privacy"),
    )


@app.route("/terms")
def terms():
    lang = session.get("lang", DEFAULT_LANG)
    return render_template(
        "terms.html",
        lang=lang,
        meta_title="Terms and Disclaimer | Career Assessment",
        meta_description="Terms, educational-use disclaimer, and limitations of the Career Assessment service.",
        canonical_url=_canonical_url("/terms"),
    )


@app.route("/set-lang", methods=["POST"])
def set_lang():
    lang = request.form.get("lang", DEFAULT_LANG)
    if lang in LANG_CONFIG:
        session["lang"] = lang
    referrer = request.referrer or "/"
    return redirect(referrer)


@app.route("/info", methods=["GET", "POST"])
def info():
    lang = session.get("lang", DEFAULT_LANG)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age_str = request.form.get("age", "").strip()
        career_situation = request.form.get("career_situation", "")

        errors = []
        if not name:
            errors.append(t("name_label", lang) + " 필수 입력")

        age = None
        if age_str:
            try:
                age = int(age_str)
                if age < 6 or age > 100:
                    errors.append("나이는 6~100 사이여야 합니다.")
            except ValueError:
                errors.append("나이를 숫자로 입력해주세요.")
        else:
            errors.append(t("age_label", lang) + " 필수 입력")

        if errors:
            return render_template(
                "info.html",
                lang=lang,
                errors=errors,
                saved_name=name,
                saved_age=age_str,
                saved_situation=career_situation,
            )

        age_group = get_age_group(age)
        plan_raw = get_assessment_plan(age_group)
        plan = _plan_to_session(plan_raw)

        session["name"] = name
        session["age"] = age
        session["age_group"] = age_group
        session["plan"] = plan
        session["current_section"] = 0
        session["answers"] = {}
        session["career_situation"] = career_situation
        session.modified = True

        return redirect(url_for("survey"))

    # GET: show form with any previously saved values
    return render_template(
        "info.html",
        lang=lang,
        errors=[],
        saved_name=session.get("name", ""),
        saved_age=session.get("age", ""),
        saved_situation=session.get("career_situation", ""),
    )


@app.route("/survey", methods=["GET"])
def survey():
    if "plan" not in session:
        return redirect(url_for("index"))

    lang = session.get("lang", DEFAULT_LANG)
    plan = session["plan"]
    sections = plan["sections"]
    current_section_idx = session.get("current_section", 0)

    if current_section_idx >= len(sections):
        return redirect(url_for("result"))

    section = sections[current_section_idx]
    sec_key = section["key"]

    questions = [
        {
            "id": q["id"],
            "text": tq(q["id"], lang),
            "dim": q["dim"],
        }
        for q in section["questions"]
    ]

    # Restore previously saved answers for this section (for back-navigation)
    saved_answers = session.get("answers", {}).get(sec_key, {})

    is_forced_choice = sec_key in ("values", "anchors")
    pick_n = 3 if sec_key == "values" else 2

    return render_template(
        "survey.html",
        lang=lang,
        section_title=section["title"],
        section_desc=section.get("desc", ""),
        section_idx=current_section_idx,
        total_sections=len(sections),
        sec_key=sec_key,
        questions=questions,
        is_forced_choice=is_forced_choice,
        pick_n=pick_n,
        saved_answers=saved_answers,
        progress_pct=int(current_section_idx / len(sections) * 100),
    )


@app.route("/survey", methods=["POST"])
def survey_post():
    if "plan" not in session:
        return redirect(url_for("index"))

    lang = session.get("lang", DEFAULT_LANG)
    plan = session["plan"]
    sections = plan["sections"]
    current_section_idx = session.get("current_section", 0)

    if current_section_idx >= len(sections):
        return redirect(url_for("result"))

    section = sections[current_section_idx]
    sec_key = section["key"]

    answers = dict(session.get("answers", {}))

    forced_choice_keys = {"values", "anchors"}

    if sec_key in forced_choice_keys:
        # forced_choice: selected dims score 5, others score 1
        selected_dims = request.form.getlist("selected_dims")
        sec_answers = {}
        for q in section["questions"]:
            qid = q["id"]
            score = 5 if q["dim"] in selected_dims else 1
            sec_answers[qid] = score
    else:
        # Likert scale
        sec_answers = {}
        for q in section["questions"]:
            qid = q["id"]
            try:
                val = int(request.form.get(f"q_{qid}", 3))
                val = max(1, min(5, val))
            except (ValueError, TypeError):
                val = 3
            sec_answers[qid] = val

    answers[sec_key] = sec_answers
    session["answers"] = answers
    session["current_section"] = current_section_idx + 1
    session.modified = True

    next_idx = current_section_idx + 1
    if next_idx >= len(sections):
        # All sections done — compute results
        return _compute_and_store_results()

    return redirect(url_for("survey"))


def _compute_and_store_results():
    """Score + match, store in session, redirect to result."""
    plan = session["plan"]
    answers = session.get("answers", {})
    age_group = session.get("age_group", "young_adult")
    name = session.get("name", "")

    # Re-hydrate plan questions with reverse flag from original data for scorer
    # score_all_modules expects the raw section dicts with full question objects
    # We rebuild from stored plan (reverse flag was dropped for non-Big5)
    # The scorer reads 'reverse' key — it's safe if missing (defaults False)
    sections_for_scorer = plan["sections"]

    try:
        results = score_all_modules(answers, plan)
        ranked = rank_careers(results, age_group, top_n=12)
    except Exception as e:
        session["result_error"] = str(e)
        session.modified = True
        return redirect(url_for("result"))

    holland_scores = results.get("holland", {})
    holland_code = _compute_holland_code(holland_scores)
    share_url = _build_share_url(name, holland_code, ranked)

    session["results"] = results
    session["holland_code"] = holland_code
    session["share_url"] = share_url
    session.modified = True

    return redirect(url_for("result"))


@app.route("/result")
def result():
    if "results" not in session and "result_error" not in session:
        return redirect(url_for("index"))

    lang = session.get("lang", DEFAULT_LANG)
    error = session.get("result_error")
    if error:
        return render_template("result.html", lang=lang, error=error)

    name = session.get("name", "")
    age_group = session.get("age_group", "young_adult")
    results = session["results"]
    ranked = rank_careers(results, age_group, top_n=12)
    holland_code = session.get("holland_code", "---")
    share_url = session.get("share_url", "")

    # Build charts (only if data present)
    holland_chart = _make_holland_chart(results) if results.get("holland") else None
    mi_chart = _make_mi_chart(results) if results.get("mi") else None
    big5_chart = _make_big5_chart(results) if results.get("big5") else None
    values_chart = _make_values_chart(results) if results.get("values") else None

    # Enrich ranked with detail info + English descriptions + global data
    for fit in ranked:
        cid = fit["career_data"].get("id", "")
        detail = CAREER_DETAIL_DB.get(cid, {})
        global_d = CAREER_GLOBAL_DATA.get(cid, {})
        # Salary: global USD if non-Korean, else Korean won
        if lang == "ko":
            fit["salary_display"] = detail.get("salary_range", fit["career_data"].get("salary_level", ""))
        else:
            fit["salary_display"] = global_d.get("salary_global", detail.get("salary_range", ""))
        # Roadmap: global English steps if non-Korean
        if lang == "ko":
            fit["roadmap_display"] = detail.get("career_path", [])
        else:
            fit["roadmap_display"] = global_d.get("roadmap", detail.get("career_path", []))
        # Description
        if lang != "ko" and cid in CAREER_DESC_EN:
            fit["desc_display"] = CAREER_DESC_EN[cid]
        else:
            fit["desc_display"] = None
        rev = CAREER_REVIEWS.get(cid, {})
        fit["review"] = rev.get(lang, rev.get("en", None))

    # AI-style insight
    insight = None
    if generate_insight and results:
        try:
            insight = generate_insight(results, lang)
        except Exception:
            insight = None

    top_career = ranked[0] if ranked else None
    top1_name = top_career["career_name"] if top_career else "-"
    top1_score = round(top_career["score"]) if top_career else 0
    categories = sorted(set(r["career_data"].get("category", "") for r in ranked if r["career_data"]))
    has_maturity = "maturity" in results
    profile_html = _build_profile_html(results)

    return render_template(
        "result.html",
        lang=lang,
        error=None,
        name=name,
        age_group=age_group,
        holland_code=holland_code,
        top1_name=top1_name,
        top1_score=top1_score,
        share_url=share_url,
        results=results,
        ranked=ranked,
        categories=categories,
        has_maturity=has_maturity,
        profile_html=profile_html,
        career_situation=session.get("career_situation", ""),
        insight=insight,
        holland_chart=holland_chart,
        mi_chart=mi_chart,
        big5_chart=big5_chart,
        values_chart=values_chart,
        career_detail_db=CAREER_DETAIL_DB,
    )


@app.route("/survey-back", methods=["POST"])
def survey_back():
    session["current_section"] = max(0, session.get("current_section", 1) - 1)
    session.modified = True
    return redirect(url_for("survey"))


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return redirect(url_for("index"))


@app.route("/download-report")
def download_report():
    if "results" not in session:
        return redirect(url_for("index"))

    name = session.get("name", "익명")
    age_group = session.get("age_group", "young_adult")
    holland_code = session.get("holland_code", "---")
    results = session["results"]
    ranked = session.get("ranked", [])
    if results:
        ranked = rank_careers(results, age_group, top_n=12)

    html_content = _generate_html_report(name, age_group, holland_code, results, ranked)

    response = make_response(html_content)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    safe_name = name.replace(" ", "_")
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_name}_진로탐색결과.html"'
    return response


# ────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────

@app.route("/analytics/event", methods=["POST"])
def analytics_event():
    payload = request.get_json(silent=True) or {}
    try:
        _store_analytics_event(payload)
    except Exception as exc:
        # Analytics must never break the user-facing app.
        app.logger.warning("analytics_event_store_failed: %s", exc)
        pass
    return ("", 204)


@app.route("/admin/analytics")
def admin_analytics():
    if not _analytics_allowed():
        return make_response("Analytics token required. Set ANALYTICS_TOKEN and open /admin/analytics?token=YOUR_TOKEN.", 403)
    days = _safe_int(request.args.get("days")) or 7
    days = max(1, min(days, 90))
    summary = _analytics_summary(days)
    return render_template(
        "analytics_dashboard.html",
        lang=session.get("lang", DEFAULT_LANG),
        summary=summary,
        meta_title="Analytics | CareersDNA",
        meta_description="Private CareersDNA analytics dashboard.",
        canonical_url=None,
    )


@app.route("/admin/analytics.json")
def admin_analytics_json():
    if not _analytics_allowed():
        return jsonify({"error": "analytics token required"}), 403
    days = _safe_int(request.args.get("days")) or 7
    days = max(1, min(days, 90))
    return jsonify(_analytics_summary(days))


@app.route("/robots.txt")
def robots_txt():
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {APP_URL}/sitemap.xml",
        "",
    ])
    response = make_response(body)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@app.route("/ads.txt")
def ads_txt():
    body = "google.com, pub-6018524927950587, DIRECT, f08c47fec0942fa0\n"
    response = make_response(body)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@app.route(f"/{INDEXNOW_KEY}.txt")
def indexnow_key_txt():
    response = make_response(f"{INDEXNOW_KEY}\n")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@app.route("/sitemap.xml")
def sitemap_xml():
    paths = ["/", "/blog", "/info", "/careers", "/privacy", "/terms"]
    paths.extend(f"/tools/category/{slug}" for slug in TOOL_CATEGORIES)
    paths.extend(f"/tools/{slug}" for slug in DAILY_TOOLS)
    paths.extend(f"/blog/{slug}" for slug in _published_blog_posts())
    paths.extend(f"/guides/{slug}" for slug in SEO_GUIDE_PAGES)
    paths.extend(f"/tests/{slug}" for slug in SEO_TEST_PAGES)
    paths.extend(f"/career/{career.get('id')}" for career in CAREERS_DB if career.get("id"))
    today = datetime.utcnow().strftime("%Y-%m-%d")
    def sitemap_meta(path: str) -> tuple[str, str]:
        if path == "/":
            return "daily", "1.0"
        if path.startswith("/tests/"):
            return "weekly", "0.9"
        if path.startswith("/guides/"):
            return "weekly", "0.9"
        if path == "/blog":
            return "daily", "0.9"
        if path.startswith("/blog/"):
            return "weekly", "0.8"
        if path.startswith("/tools/category/"):
            return "weekly", "0.9"
        if path.startswith("/tools/"):
            return "weekly", "0.8"
        if path == "/careers":
            return "weekly", "0.8"
        if path.startswith("/career/"):
            return "monthly", "0.7"
        return "monthly", "0.4"
    urls = "\n".join(
        f"""  <url>
    <loc>{APP_URL}{path}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""
        for path in paths
        for changefreq, priority in [sitemap_meta(path)]
    )
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""
    response = make_response(body)
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
