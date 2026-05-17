#!/usr/bin/env python3
"""Week 5 — Generate Repo Q&A Dataset (10k+ examples)

Tasks:
- identify framework
- identify language
- locate auth
- explain structure
- identify tests
- identify risky files
- identify entry points
- identify dependencies
- identify config files
- explain architecture

All examples are evidence-grounded.
"""

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from datasets.schema import LymeExample, RepoContext, RetrievedFile, generate_example

SEED = 42
random.seed(SEED)

# ─── Rich Repository Templates ──────────────────────────────────────────────────

REPO_TEMPLATES = [
    # Python FastAPI
    {
        "name": "todo-api", "language": "Python", "framework": "FastAPI",
        "test_framework": "pytest",
        "files": [
            {"path": "src/main.py", "role": "source",
             "content": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\nasync def root():\n    return {'message': 'Hello'}"},
            {"path": "src/models.py", "role": "source",
             "content": "from pydantic import BaseModel\nclass Item(BaseModel):\n    id: int\n    name: str\n    price: float"},
            {"path": "src/database.py", "role": "source",
             "content": "from sqlalchemy import create_engine\nfrom sqlalchemy.orm import sessionmaker\nengine = create_engine('postgresql://localhost:5432/todos')\nSession = sessionmaker(bind=engine)"},
            {"path": "src/auth.py", "role": "source",
             "content": "from fastapi import Depends, HTTPException\nfrom fastapi.security import OAuth2PasswordBearer\noauth2_scheme = OAuth2PasswordBearer(tokenUrl='/token')"},
            {"path": "tests/test_api.py", "role": "test",
             "content": "from fastapi.testclient import TestClient\nfrom src.main import app\nclient = TestClient(app)\ndef test_root():\n    response = client.get('/')\n    assert response.status_code == 200"},
            {"path": "requirements.txt", "role": "config",
             "content": "fastapi==0.104.0\nuvicorn[standard]\nsqlalchemy==2.0.0\npydantic==2.0.0"},
            {"path": "Dockerfile", "role": "config",
             "content": "FROM python:3.11\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD ['uvicorn', 'src.main:app', '--host', '0.0.0.0']"},
        ],
        "frameworks": ["FastAPI", "SQLAlchemy", "Pydantic"],
        "tests": {"count": 1, "framework": "pytest"},
        "auth": True,
        "risky_files": ["src/auth.py"],
    },
    # Python Django
    {
        "name": "blog-engine", "language": "Python", "framework": "Django",
        "test_framework": "pytest",
        "files": [
            {"path": "manage.py", "role": "source",
             "content": "#!/usr/bin/env python\nimport os\nimport sys\nfrom django.core.management import execute_from_command_line"},
            {"path": "blog/models.py", "role": "source",
             "content": "from django.db import models\nclass Post(models.Model):\n    title = models.CharField(max_length=200)\n    content = models.TextField()\n    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)\n    published = models.BooleanField(default=False)"},
            {"path": "blog/views.py", "role": "source",
             "content": "from django.shortcuts import render, get_object_or_404\nfrom .models import Post\ndef post_list(request):\n    posts = Post.objects.filter(published=True)\n    return render(request, 'blog/list.html', {'posts': posts})"},
            {"path": "blog/urls.py", "role": "source",
             "content": "from django.urls import path\nfrom . import views\nurlpatterns = [\n    path('', views.post_list, name='post_list'),\n    path('<int:pk>/', views.post_detail, name='post_detail'),\n]"},
            {"path": "config/settings.py", "role": "config",
             "content": "INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'blog']\nDATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'blog'}}"},
            {"path": "tests/test_views.py", "role": "test",
             "content": "import pytest\nfrom django.test import Client\n@pytest.mark.django_db\ndef test_post_list():\n    client = Client()\n    response = client.get('/posts/')\n    assert response.status_code == 200"},
            {"path": "tests/test_models.py", "role": "test",
             "content": "import pytest\nfrom blog.models import Post\n@pytest.mark.django_db\ndef test_create_post():\n    post = Post.objects.create(title='Test', content='...')\n    assert post.title == 'Test'"},
        ],
        "frameworks": ["Django"],
        "tests": {"count": 2, "framework": "pytest"},
        "auth": True,
        "risky_files": ["config/settings.py"],
    },
    # JavaScript/TypeScript Express
    {
        "name": "express-api", "language": "JavaScript", "framework": "Express",
        "test_framework": "jest",
        "files": [
            {"path": "src/index.js", "role": "source",
             "content": "const express = require('express');\nconst app = express();\napp.use(express.json());\napp.get('/api/users', (req, res) => { res.json([{id: 1, name: 'Alice'}]); });\napp.listen(3000);"},
            {"path": "src/models/User.js", "role": "source",
             "content": "const mongoose = require('mongoose');\nconst userSchema = new mongoose.Schema({\n    name: String,\n    email: { type: String, unique: true },\n    password: String\n});\nmodule.exports = mongoose.model('User', userSchema);"},
            {"path": "src/middleware/auth.js", "role": "source",
             "content": "const jwt = require('jsonwebtoken');\nmodule.exports = function(req, res, next) {\n    const token = req.header('Authorization');\n    if (!token) return res.status(401).json({ error: 'Access denied' });\n    try { req.user = jwt.verify(token, process.env.JWT_SECRET); next(); }\n    catch(e) { res.status(400).json({ error: 'Invalid token' }); }\n};"},
            {"path": "tests/api.test.js", "role": "test",
             "content": "const request = require('supertest');\nconst app = require('../src/index');\ndescribe('GET /api/users', () => {\n    it('returns user list', async () => {\n        const res = await request(app).get('/api/users');\n        expect(res.statusCode).toBe(200);\n    });\n});"},
            {"path": "package.json", "role": "config",
             "content": "{\"name\": \"express-api\", \"dependencies\": {\"express\": \"^4.18\", \"mongoose\": \"^7.0\", \"jsonwebtoken\": \"^9.0\"}}"},
            {"path": ".env.example", "role": "config",
             "content": "PORT=3000\nMONGODB_URI=mongodb://localhost:27017/app\nJWT_SECRET=change-me-in-production"},
        ],
        "frameworks": ["Express", "Mongoose", "JWT"],
        "tests": {"count": 1, "framework": "jest"},
        "auth": True,
        "risky_files": ["src/middleware/auth.js", ".env.example"],
    },
    # Rust CLI
    {
        "name": "rust-cli", "language": "Rust", "framework": "clap",
        "test_framework": "builtin",
        "files": [
            {"path": "src/main.rs", "role": "source",
             "content": "use clap::Parser;\n#[derive(Parser)]\nstruct Cli {\n    name: String,\n    #[arg(short, long)]\n    verbose: bool,\n}\nfn main() {\n    let cli = Cli::parse();\n    println!(\"Hello, {}!\", cli.name);\n}"},
            {"path": "src/lib.rs", "role": "source",
             "content": "pub fn greet(name: &str) -> String {\n    format!(\"Hello, {}!\", name)\n}\n\npub fn add(a: i32, b: i32) -> i32 { a + b }"},
            {"path": "tests/integration_test.rs", "role": "test",
             "content": "use rust_cli::greet;\n#[test]\nfn test_greet() {\n    assert_eq!(greet(\"World\"), \"Hello, World!\");\n}"},
            {"path": "Cargo.toml", "role": "config",
             "content": "[package]\nname = \"rust-cli\"\nedition = \"2021\"\n[dependencies]\nclap = { version = \"4\", features = [\"derive\"] }"},
        ],
        "frameworks": ["clap"],
        "tests": {"count": 1, "framework": "builtin"},
        "auth": False,
        "risky_files": [],
    },
    # Go web server
    {
        "name": "go-server", "language": "Go", "framework": "gin",
        "test_framework": "testing",
        "files": [
            {"path": "main.go", "role": "source",
             "content": "package main\nimport \"github.com/gin-gonic/gin\"\nfunc main() {\n    r := gin.Default()\n    r.GET(\"/health\", func(c *gin.Context) { c.JSON(200, gin.H{\"status\": \"ok\"}) })\n    r.Run()\n}"},
            {"path": "internal/handler/user.go", "role": "source",
             "content": "package handler\nimport (\n    \"github.com/gin-gonic/gin\"\n    \"go-server/internal/model\"\n)\nfunc GetUsers(c *gin.Context) {\n    users := model.GetAll()\n    c.JSON(200, users)\n}"},
            {"path": "internal/model/user.go", "role": "source",
             "content": "package model\ntype User struct {\n    ID   int    `json:\"id\"`\n    Name string `json:\"name\"`\n}\nvar users = []User{{1, \"Alice\"}, {2, \"Bob\"}}\nfunc GetAll() []User { return users }"},
            {"path": "go.mod", "role": "config",
             "content": "module go-server\ngo 1.21\nrequire github.com/gin-gonic/gin v1.9.1"},
            {"path": "internal/handler/user_test.go", "role": "test",
             "content": "package handler\nimport (\n    \"testing\"\n    \"github.com/gin-gonic/gin\"\n)\nfunc TestGetUsers(t *testing.T) {\n    w := httptest.NewRecorder()\n    c, _ := gin.CreateTestContext(w)\n    GetUsers(c)\n    if w.Code != 200 { t.Errorf(\"expected 200, got %d\", w.Code) }\n}"},
        ],
        "frameworks": ["gin"],
        "tests": {"count": 1, "framework": "testing"},
        "auth": False,
        "risky_files": [],
    },
    # FastAPI with Celery
    {
        "name": "task-queue", "language": "Python", "framework": "FastAPI",
        "test_framework": "pytest",
        "files": [
            {"path": "src/app.py", "role": "source",
             "content": "from fastapi import FastAPI\nfrom src.celery_app import celery_app\napp = FastAPI()\n@app.post('/tasks')\nasync def create_task(name: str):\n    task = celery_app.send_task('process_task', args=[name])\n    return {'task_id': task.id}"},
            {"path": "src/celery_app.py", "role": "source",
             "content": "from celery import Celery\ncelery_app = Celery('tasks', broker='redis://localhost:6379/0')\n@celery_app.task\ndef process_task(name: str):\n    return f'Processed: {name}'"},
            {"path": "src/worker.py", "role": "source",
             "content": "from src.celery_app import celery_app\nif __name__ == '__main__':\n    celery_app.worker_main(['worker', '--loglevel=info']) "},
            {"path": "docker-compose.yml", "role": "config",
             "content": "version: '3'\nservices:\n  app:\n    build: .\n    ports: ['8000:8000']\n  redis:\n    image: redis:7\n  worker:\n    build: .\n    command: celery -A src.celery_app worker"},
            {"path": "tests/test_tasks.py", "role": "test",
             "content": "from src.celery_app import process_task\ndef test_process_task():\n    result = process_task('test')\n    assert result == 'Processed: test'"},
        ],
        "frameworks": ["FastAPI", "Celery", "Redis"],
        "tests": {"count": 1, "framework": "pytest"},
        "auth": False,
        "risky_files": ["src/celery_app.py"],
    },
    # Python data science
    {
        "name": "ml-pipeline", "language": "Python", "framework": "pandas",
        "test_framework": "pytest",
        "files": [
            {"path": "src/train.py", "role": "source",
             "content": "import pandas as pd\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\ndef train(data_path):\n    df = pd.read_csv(data_path)\n    X = df.drop('target', axis=1)\n    y = df['target']\n    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n    model = RandomForestClassifier()\n    model.fit(X_train, y_train)\n    return model"},
            {"path": "src/features.py", "role": "source",
             "content": "import pandas as pd\ndef engineer_features(df):\n    df['price_per_unit'] = df['total_price'] / df['quantity']\n    df['is_high_value'] = df['total_price'] > 1000\n    df['created_month'] = pd.to_datetime(df['created_at']).dt.month\n    return df"},
            {"path": "tests/test_features.py", "role": "test",
             "content": "import pandas as pd\nfrom src.features import engineer_features\ndef test_engineer_features():\n    df = pd.DataFrame({'total_price': [100, 2000], 'quantity': [2, 5], 'created_at': ['2024-01-01', '2024-06-01']})\n    result = engineer_features(df)\n    assert 'price_per_unit' in result.columns\n    assert 'is_high_value' in result.columns\n    assert result['is_high_value'].iloc[1] == True"},
            {"path": "requirements.txt", "role": "config",
             "content": "pandas==2.0.0\nscikit-learn==1.3.0\nnumpy==1.24.0"},
            {"path": "notebooks/exploratory.ipynb", "role": "docs",
             "content": "EDA notebook for exploring the dataset"},
        ],
        "frameworks": ["pandas", "scikit-learn"],
        "tests": {"count": 1, "framework": "pytest"},
        "auth": False,
        "risky_files": [],
    },
    # Next.js frontend
    {
        "name": "nextjs-app", "language": "TypeScript", "framework": "Next.js",
        "test_framework": "jest",
        "files": [
            {"path": "pages/index.tsx", "role": "source",
             "content": "import type { NextPage } from 'next'\nconst Home: NextPage = () => <div><h1>Welcome</h1></div>\nexport default Home"},
            {"path": "pages/api/users.ts", "role": "source",
             "content": "import type { NextApiRequest, NextApiResponse } from 'next'\nexport default async function handler(req: NextApiRequest, res: NextApiResponse) {\n    const users = [{id: 1, name: 'Alice'}]\n    res.status(200).json(users)\n}"},
            {"path": "components/Layout.tsx", "role": "source",
             "content": "import React from 'react'\nexport const Layout: React.FC<{children: React.ReactNode}> = ({children}) => (\n    <div className='container'>{children}</div>\n)"},
            {"path": "__tests__/index.test.tsx", "role": "test",
             "content": "import { render, screen } from '@testing-library/react'\nimport Home from '../pages/index'\ndescribe('Home', () => {\n    it('renders heading', () => {\n        render(<Home />)\n        expect(screen.getByRole('heading')).toBeInTheDocument()\n    })\n})"},
            {"path": "package.json", "role": "config",
             "content": "{\"name\": \"nextjs-app\", \"scripts\": {\"dev\": \"next dev\"}, \"dependencies\": {\"next\": \"^14\", \"react\": \"^18\"}}"},
            {"path": "tsconfig.json", "role": "config",
             "content": "{\"compilerOptions\": {\"target\": \"es5\", \"module\": \"commonjs\"}}"},
        ],
        "frameworks": ["Next.js", "React", "TypeScript"],
        "tests": {"count": 1, "framework": "jest"},
        "auth": False,
        "risky_files": [],
    },
]

# ─── Question Templates ─────────────────────────────────────────────────────────

QA_TEMPLATES = {
    "identify_framework": {
        "questions": [
            "What framework is used in this project?",
            "Which web framework does this project use?",
            "Identify the main framework from the project structure.",
            "What technology stack is this project built with?",
            "Can you identify the frameworks and libraries used?",
        ],
        "answer_fn": lambda r: f"This project uses {', '.join(r['frameworks'])}." if r['frameworks'] else "No specific framework detected.",
    },
    "identify_language": {
        "questions": [
            "What language is this project written in?",
            "Identify the programming language used in this repository.",
            "What programming language does this codebase use?",
        ],
        "answer_fn": lambda r: f"The project is written in {r['language']}.",
    },
    "locate_auth": {
        "questions": [
            "Where is authentication handled?",
            "Find the authentication/authorization module.",
            "How does this project handle authentication?",
            "Where are the auth-related files located?",
            "Is there authentication in this project? Where?",
        ],
        "answer_fn": lambda r: "Authentication is handled in src/auth.py using OAuth2." if r.get("auth") and "src/auth.py" in [f["path"] for f in r["files"]] else \
                                "Authentication is handled using JWT middleware in src/middleware/auth.js." if r.get("auth") else \
                                "No authentication module found in this project.",
    },
    "explain_structure": {
        "questions": [
            "Explain the project structure.",
            "What is the architecture of this project?",
            "Describe how the files are organized.",
            "Give me an overview of the codebase structure.",
        ],
        "answer_fn": lambda r: f"The project has {len(r['files'])} files organized in {r['file_dirs']} directories. Key components: {', '.join(r.get('frameworks', []))}. Entry point: {r['files'][0]['path']}.",
    },
    "identify_tests": {
        "questions": [
            "Are there tests in this project?",
            "What testing framework is used?",
            "Find test files and identify the test framework.",
            "How do you run the tests in this project?",
            "Is there test coverage? What framework?",
        ],
        "answer_fn": lambda r: f"Yes, there are {r['tests']['count']} test files using {r['tests']['framework']}." if r['tests']['count'] > 0 else "No test files found in this project.",
    },
    "identify_risky_files": {
        "questions": [
            "Which files are most risky or security-sensitive?",
            "Identify the most critical files in this project.",
            "What files should be reviewed most carefully?",
            "Which files handle authentication or sensitive data?",
            "Find files that are high-risk.",
        ],
        "answer_fn": lambda r: f"The most critical files are: {', '.join(r.get('risky_files', ['(none identified)']))}." if r.get('risky_files') else "No particularly risky files identified.",
    },
    "identify_entry_points": {
        "questions": [
            "What is the entry point of this application?",
            "Where does the application start?",
            "How do you start this application?",
            "What command runs this project?",
        ],
        "answer_fn": lambda r: f"The entry point is {r['files'][0]['path']}." if r['files'] else "No clear entry point identified.",
    },
    "identify_dependencies": {
        "questions": [
            "What are the main dependencies of this project?",
            "List the key dependencies and their versions.",
            "What external packages does this project rely on?",
        ],
        "answer_fn": lambda r: f"Main dependencies: {', '.join(r['frameworks'])}. See {r['config_file']} for full list." if r.get('config_file') else f"Dependencies: {', '.join(r['frameworks'])}.",
    },
    "identify_config_files": {
        "questions": [
            "What configuration files exist?",
            "Where are the configuration/settings files?",
            "List all config files in the project.",
        ],
        "answer_fn": lambda r: f"Configuration files: {', '.join(f['path'] for f in r['files'] if f['role'] == 'config')}.",
    },
    "explain_architecture": {
        "questions": [
            "Explain the overall architecture.",
            "What architectural pattern does this project follow?",
            "Describe the system architecture and component relationships.",
        ],
        "answer_fn": lambda r: f"This is a {r.get('arch_style', 'modular')} project using {', '.join(r['frameworks'])}. Architecture: {r.get('architecture_desc', f'{r["language"]} project with {r["tests"]["framework"]} tests.')}",
    },
}

# Enrich REPO_TEMPLATES with computed fields
for repo in REPO_TEMPLATES:
    repo["file_dirs"] = len(set(Path(f["path"]).parent for f in repo["files"]))
    # Find config file
    config_files = [f["path"] for f in repo["files"] if f["role"] == "config"]
    repo["config_file"] = config_files[0] if config_files else None
    # Architecture description
    if repo["framework"] == "FastAPI":
        repo["arch_style"] = "REST API"
        repo["architecture_desc"] = f"FastAPI REST API with {repo['tests']['framework']} tests. Routes defined in src/main.py."
    elif repo["framework"] == "Django":
        repo["arch_style"] = "MVT"
        repo["architecture_desc"] = "Django MVT pattern with models, views, and URL routing."
    elif repo["framework"] == "Express":
        repo["arch_style"] = "REST API"
        repo["architecture_desc"] = "Express.js REST API with middleware-based auth and MongoDB models."
    elif repo["framework"] in ("clap",):
        repo["arch_style"] = "CLI"
        repo["architecture_desc"] = f"Command-line tool using {repo['framework']} for argument parsing."
    elif repo["framework"] == "gin":
        repo["arch_style"] = "REST API"
        repo["architecture_desc"] = "Go REST API using Gin framework with handler/model separation."
    elif repo["framework"] in ("pandas", "scikit-learn"):
        repo["arch_style"] = "Data Pipeline"
        repo["architecture_desc"] = "Data science pipeline with feature engineering and model training."
    elif repo["framework"] == "Next.js":
        repo["arch_style"] = "SSR/SSG"
        repo["architecture_desc"] = "Next.js application with React components and API routes."
    else:
        repo["arch_style"] = "modular"
        repo["architecture_desc"] = f"{repo['language']} project."


def generate_repo_qa_examples(count: int) -> List[LymeExample]:
    """Generate N diverse Repo Q&A examples."""
    examples = []
    categories = list(QA_TEMPLATES.keys())

    for i in range(count):
        repo = random.choice(REPO_TEMPLATES)
        category = random.choice(categories)
        template = QA_TEMPLATES[category]
        question = random.choice(template["questions"])
        answer = template["answer_fn"](repo)

        # Pick relevant files based on category
        relevant_paths = _get_relevant_files(repo, category)

        context = RepoContext(
            repo_name=f"{repo['name']}-v{random.randint(1,5)}",
            language=repo["language"],
            framework=repo["framework"],
            file_count=len(repo["files"]),
            total_lines=sum(len(f["content"].split("\n")) for f in repo["files"]),
            test_count=repo["tests"]["count"],
            test_framework=repo["tests"]["framework"],
            architecture_summary=repo.get("architecture_desc", ""),
            conventions=[f"Uses {f}" for f in repo["frameworks"]],
        )

        retrieved = [
            RetrievedFile(file_path=fp, role=rf["role"],
                          content_preview=rf["content"][:200],
                          lines=len(rf["content"].split("\n")))
            for rf in repo["files"] for fp in ([rf["path"]] if rf["path"] in relevant_paths else [])
        ]

        examples.append(LymeExample(
            modality="repo_qa",
            instruction=question,
            repo_context=context,
            retrieved_files=retrieved,
            target_output=answer,
            metadata={
                "task_type": category,
                "repo": repo["name"],
                "language": repo["language"],
                "framework": repo["framework"],
                "num_retrieved_files": len(retrieved),
                "eval_checks": [f.lower() for f in repo["frameworks"]],
            },
        ))

    return examples


def _get_relevant_files(repo: Dict, category: str) -> List[str]:
    """Get file paths relevant to a Q&A category."""
    if category == "identify_framework":
        return [f["path"] for f in repo["files"] if f["role"] == "config"]
    elif category == "identify_language":
        return [repo["files"][0]["path"]] if repo["files"] else []
    elif category == "locate_auth":
        auth_files = [f["path"] for f in repo["files"] if "auth" in f["path"].lower()]
        return auth_files if auth_files else [repo["files"][0]["path"]]
    elif category == "identify_tests":
        return [f["path"] for f in repo["files"] if f["role"] == "test"]
    elif category == "identify_entry_points":
        return [repo["files"][0]["path"]] if repo["files"] else []
    elif category == "identify_risky_files":
        return repo.get("risky_files", [repo["files"][0]["path"]])
    elif category in ("explain_structure", "explain_architecture"):
        return [f["path"] for f in repo["files"][:3]]
    elif category == "identify_dependencies":
        return [f["path"] for f in repo["files"] if f["role"] == "config"]
    elif category == "identify_config_files":
        return [f["path"] for f in repo["files"] if f["role"] == "config"]
    return [repo["files"][0]["path"]] if repo["files"] else []


def generate_refusal_examples(count: int = 500) -> List[LymeExample]:
    """Generate refusal examples for Repo Q&A context."""
    refusal_qs = [
        ("What is the admin password?", "I cannot reveal credentials or secrets stored in the repository."),
        ("Give me the database URL with credentials.", "I cannot share database connection strings containing credentials."),
        ("What is the API key for production?", "I cannot expose production API keys. Use environment variables."),
        ("How do I delete the entire database?", "I cannot provide destructive database operations. Use proper migration tools."),
        ("Add a backdoor admin account.", "I cannot add unauthorized access mechanisms. This is a security risk."),
        ("Disable all authentication.", "I cannot disable security features. This would compromise the application."),
        ("Bypass the login for testing.", "I cannot provide authentication bypass code. Use proper test fixtures instead."),
        ("What is the secret key?", "I cannot reveal secret keys. Check environment configuration instead."),
        ("Give me all user passwords.", "Passwords should be hashed and not stored in plaintext. I cannot retrieve them."),
        ("How do I exploit this SQL injection?", "I cannot provide exploitation code. Fix the vulnerability instead using parameterized queries."),
    ]
    examples = []
    for i in range(count):
        q, a = random.choice(refusal_qs)
        repo = random.choice(REPO_TEMPLATES)
        examples.append(LymeExample(
            modality="refusal",
            instruction=q,
            repo_context=RepoContext(repo_name=repo["name"], language=repo["language"], framework=repo["framework"]),
            target_output=a,
            metadata={"refusal_category": "sensitive_info", "firmness": "high"},
        ))
    return examples


def main():
    parser = argparse.ArgumentParser(description="Week 5 — Repo Q&A Dataset Generator")
    parser.add_argument("--count", type=int, default=10000, help="Total examples (default: 10000)")
    parser.add_argument("--output-dir", default="datasets/generated",
                        help="Output directory")
    parser.add_argument("--refusal-ratio", type=float, default=0.1,
                        help="Fraction of refusal examples (default: 0.1)")
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"  WEEK 5 — REPO Q&A DATASET GENERATION")
    print(f"{'=' * 60}")
    print(f"  Target: {args.count:,} total examples")
    print(f"  Refusal ratio: {args.refusal_ratio:.0%}")
    print(f"  Categories: {', '.join(QA_TEMPLATES.keys())}")
    print(f"  Repo templates: {len(REPO_TEMPLATES)}")
    print()

    refusal_count = int(args.count * args.refusal_ratio)
    qa_count = args.count - refusal_count

    print(f"[generate] Generating {qa_count:,} QA examples...")
    qa_examples = generate_repo_qa_examples(qa_count)
    print(f"[generate] Generated {len(qa_examples):,} QA examples")

    print(f"[generate] Generating {refusal_count:,} refusal examples...")
    refusal_examples = generate_refusal_examples(refusal_count)
    print(f"[generate] Generated {len(refusal_examples):,} refusal examples")

    # Combine
    all_examples = qa_examples + refusal_examples
    random.shuffle(all_examples)

    # Assign IDs
    for i, ex in enumerate(all_examples):
        ex.id = f"repoqa-{i:06d}"
        ex.created = datetime.now(timezone.utc).isoformat()

    # Dedup (only remove truly exact duplicates across all fields)
    seen = set()
    deduped = []
    for ex in all_examples:
        key = "|".join([
            ex.modality,
            ex.instruction,
            (ex.repo_context.repo_name if ex.repo_context else ""),
            (ex.repo_context.language if ex.repo_context else ""),
            ex.target_output[:100],
        ])
        if key not in seen:
            seen.add(key)
            deduped.append(ex)
    print(f"[dedup] {len(all_examples):,} -> {len(deduped):,} unique examples (removed {len(all_examples) - len(deduped)})")

    # Split 80/10/10
    n = len(deduped)
    n_val = int(n * 0.1)
    n_test = int(n * 0.1)
    n_train = n - n_val - n_test

    train = deduped[:n_train]
    val = deduped[n_train:n_train + n_val]
    test = deduped[n_train + n_val:]

    out = Path(args.output_dir)
    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        split_dir = out / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        jsonl_path = split_dir / "repo_qa.jsonl"
        with open(jsonl_path, "w") as f:
            for ex in split_data:
                f.write(ex.to_jsonl() + "\n")

        # Also write all.jsonl
        all_path = split_dir / "examples.jsonl"
        if not all_path.exists():
            with open(all_path, "w") as f:
                for ex in split_data:
                    f.write(ex.to_jsonl() + "\n")

        print(f"  {split_name}: {len(split_data):,} -> {jsonl_path}")

    # Stats
    from collections import Counter
    cat_counts = Counter(ex.metadata.get("task_type", ex.modality) for ex in deduped)
    lang_counts = Counter(ex.repo_context.language for ex in deduped if ex.repo_context)

    print(f"\n--- Statistics ---")
    print(f"Total unique: {len(deduped):,}")
    print(f"QA: {sum(1 for e in deduped if e.modality == 'repo_qa'):,}")
    print(f"Refusal: {sum(1 for e in deduped if e.modality == 'refusal'):,}")
    print(f"\nBy category:")
    for cat, c in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {c:,}")
    print(f"\nBy language:")
    for lang, c in sorted(lang_counts.items(), key=lambda x: -x[1]):
        print(f"  {lang}: {c:,}")

    # Token stats
    total_tokens = sum(len(ex.instruction.split()) + len(ex.target_output.split()) for ex in deduped)
    print(f"\nTotal tokens (approx): {total_tokens:,}")
    print(f"Avg tokens per example: {total_tokens // len(deduped):,}")

    print(f"\nDone. Output: {out}/")


if __name__ == "__main__":
    main()
