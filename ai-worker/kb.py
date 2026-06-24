"""Career knowledge base (curated, static).

A small set of career-guidance documents the AI mentor can retrieve from. Kept
as plain Python so it's trivial to edit/extend and ships inside the worker - no
separate data store or files to provision at deploy time.

Each entry is one retrievable chunk. Add more dicts to grow the KB; rag.py will
index them automatically on startup.

Location:
    E:\\campus-ai\\ai-worker\\kb.py
"""

CAREER_KB: list[dict] = [
    {
        "id": "role-backend",
        "topic": "Backend Developer",
        "text": (
            "Backend developer roles expect strong fundamentals in at least one "
            "server language (Python, Java, Go, or Node.js), REST/GraphQL API "
            "design, relational databases and SQL, authentication and "
            "authorization, caching, and basic system design. Employers value "
            "projects that show real APIs with a database, tests, and "
            "deployment (Docker, a cloud host). Knowing Git, HTTP, and how to "
            "debug production issues is expected. A standout fresher has 1-2 "
            "deployed backend projects and can explain their data model and "
            "trade-offs."
        ),
    },
    {
        "id": "role-frontend",
        "topic": "Frontend Developer",
        "text": (
            "Frontend developer roles expect solid HTML, CSS, and JavaScript, a "
            "modern framework (React/Next.js or Vue), state management, "
            "responsive design, accessibility, and calling APIs. Employers like "
            "to see polished, deployed UIs, attention to UX, and reusable "
            "components. TypeScript is increasingly expected. A strong portfolio "
            "shows 2-3 real interfaces, not just tutorials."
        ),
    },
    {
        "id": "role-data-ml",
        "topic": "Data Science / ML Engineer",
        "text": (
            "Data and ML roles expect Python, pandas/NumPy, SQL, statistics, and "
            "core ML (scikit-learn, model evaluation). ML engineering also "
            "values deploying models behind an API, handling data pipelines, and "
            "basic MLOps. For GenAI roles, knowledge of LLMs, prompt design, RAG, "
            "embeddings, and vector databases is a strong differentiator. "
            "End-to-end projects (data to deployed model/app) beat isolated "
            "notebooks."
        ),
    },
    {
        "id": "resume-fresher",
        "topic": "Resume Best Practices (Freshers)",
        "text": (
            "A strong fresher resume is one page, reverse-chronological, and "
            "led by projects and skills rather than objectives. Use action verbs "
            "and quantify impact (e.g. 'reduced API latency 40%', 'handled 500 "
            "users'). List only skills you can defend in an interview. Include "
            "links to GitHub and live demos. Tailor keywords to the job "
            "description so it passes ATS screening. Avoid vague buzzwords and "
            "unverified claims - depth beats a long list."
        ),
    },
    {
        "id": "interview-prep",
        "topic": "Technical Interview Preparation",
        "text": (
            "Placement interviews usually have rounds: aptitude/coding (DSA), a "
            "technical/project round, and an HR round. Practice data structures "
            "and algorithms (arrays, strings, hashing, trees, graphs, DP) on "
            "LeetCode/HackerRank. Be ready to deep-dive your own projects: "
            "architecture, trade-offs, and what you'd improve. Use the STAR "
            "method for behavioral questions. Mock interviews and explaining your "
            "thinking out loud matter as much as the final answer."
        ),
    },
    {
        "id": "dsa-placement",
        "topic": "DSA & Problem Solving",
        "text": (
            "For campus placements, consistent DSA practice is critical. Aim for "
            "steady daily practice over cramming: master patterns (two pointers, "
            "sliding window, recursion/backtracking, binary search, graphs, "
            "dynamic programming). Track 150-250 well-chosen problems rather than "
            "thousands randomly. Time yourself and review optimal solutions. "
            "Strong DSA clears the first filter at most product companies."
        ),
    },
    {
        "id": "internships",
        "topic": "Internships & Experience",
        "text": (
            "Internships are the single biggest signal for freshers: they show "
            "real-world experience and often convert to full-time offers. Apply "
            "early, target open-source programs, startups, and college tie-ups. "
            "Even unpaid but substantial project work counts if you can show "
            "shipped outcomes. Document what you built and the measurable impact "
            "so it strengthens your resume and verified profile."
        ),
    },
    {
        "id": "projects-portfolio",
        "topic": "Building a Project Portfolio",
        "text": (
            "Recruiters trust demonstrated work over claimed skills. Build 2-4 "
            "substantial, end-to-end projects that solve a real problem, are "
            "deployed, and have clean GitHub repos with READMEs. Depth matters: "
            "one well-engineered project with tests, auth, and deployment beats "
            "many half-finished ones. Be able to explain every design decision. "
            "Verified, real contributions carry far more weight than unverifiable "
            "claims."
        ),
    },
    {
        "id": "soft-skills",
        "topic": "Communication & Soft Skills",
        "text": (
            "Communication, teamwork, and ownership strongly influence hiring "
            "decisions. Practice explaining technical work simply, writing clear "
            "documentation, and collaborating in teams. In group projects, a "
            "clearly owned, verified contribution signals reliability. HR rounds "
            "assess attitude, adaptability, and culture fit - prepare honest "
            "stories about challenges and learning."
        ),
    },
    {
        "id": "open-source",
        "topic": "Open Source Contributions",
        "text": (
            "Contributing to open source builds real collaboration experience: "
            "reading large codebases, following contribution guidelines, writing "
            "tests, and handling code review. Start with documentation fixes or "
            "'good first issue' labels, then take on features. Merged pull "
            "requests are public, verifiable proof of skill and are valued by "
            "recruiters."
        ),
    },
    {
        "id": "attendance-eligibility",
        "topic": "Attendance & Placement Eligibility",
        "text": (
            "Many companies and colleges set a minimum attendance (often 75%) and "
            "CGPA cutoff (commonly 6.0-7.0) for placement eligibility. Low "
            "attendance or backlogs can disqualify a student before skills are "
            "even considered. Maintaining good attendance and clearing backlogs "
            "early keeps the maximum number of drives open to you."
        ),
    },
]
