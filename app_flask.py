import os
import sys
import json
import base64
import hashlib
import sqlite3
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
ANALYTICS_DB = os.environ.get(
    "ANALYTICS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "analytics.sqlite3"),
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
        "csv_to_json",
    }:
        return "developer"
    if tool_type in {"image_resizer", "image_compressor", "image_to_webp"}:
        return "image"
    if tool_type in {"qr_code_generator", "invoice_generator"}:
        return "business"
    if tool_type in {"word_counter", "case_converter", "text_repeater", "text_diff", "markdown_previewer"}:
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


@app.route("/")
def index():
    lang = session.get("lang", DEFAULT_LANG)
    shared_data = None
    r_param = request.args.get("r")
    if r_param:
        shared_data = _decode_share_param(r_param)
    return render_template(
        "welcome.html",
        lang=lang,
        LANG_CONFIG=LANG_CONFIG,
        shared_data=shared_data,
        test_pages=SEO_TEST_PAGES,
        guide_pages=SEO_GUIDE_PAGES,
        featured_careers=[_career_display(c, lang) for c in _top_career_sample(8)],
        meta_title="Free Career Test | Career Aptitude Test and Job Match",
        meta_description="Take a free career test to compare interests, strengths, personality, and work values against 174 career profiles with practical next steps.",
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
    lang = session.get("lang", DEFAULT_LANG)
    return render_template(
        "tools_index.html",
        lang=lang,
        tools=DAILY_TOOLS,
        categories=TOOL_CATEGORIES,
        grouped_tools=_tools_by_category(),
        meta_title="Daily Tools | Free Word Counter, Timer, Picker, and Habit Tracker",
        meta_description="Free daily tools for repeat use: word counter, random picker, Pomodoro timer, habit tracker, and decision wheel.",
        canonical_url=_canonical_url("/tools"),
    )


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
    related_tools = {k: v for k, v in DAILY_TOOLS.items() if k != slug}
    return render_template(
        "tool_page.html",
        lang=lang,
        slug=slug,
        tool=tool,
        related_tools=related_tools,
        meta_title=f"{tool['title']} | Free Daily Tool",
        meta_description=tool["description"],
        canonical_url=_canonical_url(f"/tools/{slug}"),
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
    except Exception:
        # Analytics must never break the user-facing app.
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


@app.route("/sitemap.xml")
def sitemap_xml():
    paths = ["/", "/careers", "/privacy", "/terms"]
    paths.append("/tools")
    paths.append("/pdf-tools")
    paths.extend(f"/tools/category/{slug}" for slug in TOOL_CATEGORIES)
    paths.extend(f"/tools/{slug}" for slug in DAILY_TOOLS)
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
        if path == "/tools":
            return "daily", "0.9"
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
