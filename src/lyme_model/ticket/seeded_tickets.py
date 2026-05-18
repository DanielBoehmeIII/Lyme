"""15 seeded client tickets simulating real paid engineering work.

Each ticket includes:
- ambiguous requirements (like real clients)
- hidden tests (edge cases the client didn't mention)
- architecture constraints
- difficulty score and revenue estimate
"""

from .models import ClientTicket, TicketDifficulty, HiddenTest, ArchitectureConstraint

SEEDED_TICKETS: list[ClientTicket] = [
    ClientTicket(
        id="ticket-001",
        title="Add pagination to user list endpoint",
        description="The client has a REST API with a GET /users endpoint that returns all users. "
                    "They need pagination added. 'Just add page and limit parameters, it's straightforward.' "
                    "The client hasn't specified defaults, max page size, or what happens with invalid values.",
        ambiguous_elements=[
            "Default page size not specified",
            "Maximum page size not specified",
            "Error handling for invalid page/limit values not defined",
            "Response format for paginated results not specified",
            "Whether to include total count in response",
        ],
        acceptance_criteria=[
            "GET /users?page=1&limit=10 returns first 10 users",
            "GET /users?page=2&limit=10 returns next 10 users",
            "response includes total_count field",
            "default limit is 20 when not specified",
            "max limit is 100",
        ],
        hidden_tests=[
            HiddenTest("Negative page number returns 400", "error_handling", "page=-1", 5),
            HiddenTest("Page 0 is treated as page 1", "edge_case", "page=0", 3),
            HiddenTest("Limit > 100 is clamped to 100", "validation", "limit=999", 4),
            HiddenTest("String values for page/limit return 400", "type_safety", "page=abc", 3),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use existing database connection pool", "infrastructure", "hard"),
            ArchitectureConstraint("Response format must follow existing API conventions", "style", "medium"),
            ArchitectureConstraint("No new dependencies allowed", "dependency", "hard"),
        ],
        difficulty=TicketDifficulty.MEDIUM,
        difficulty_score=0.55,
        estimated_revenue=250.0,
        estimated_hours=4.0,
        client_context="Startup with existing Flask REST API. 3-person team. Needs this done in 2 days.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Check existing API response format in routes.py", "Use request.args.get() with defaults"],
        tags=["api", "pagination", "rest"],
    ),
    ClientTicket(
        id="ticket-002",
        title="Add search/filter to inventory dashboard",
        description="The client has an inventory management dashboard showing products in a table. "
                    "They want to add search by product name and filter by category/status. "
                    "'Just add a search bar and some dropdowns, should be easy.' No wireframe provided. "
                    "No specification of whether search is client-side or server-side.",
        ambiguous_elements=[
            "Client-side vs server-side search not specified",
            "Debounce timing for search input not specified",
            "Whether multiple filters combine with AND or OR",
            "Empty state design not specified",
            "Whether to show results count",
        ],
        acceptance_criteria=[
            "Search by product name filters the table",
            "Filter by category dropdown works",
            "Filter by status dropdown works",
            "Search and filter can be combined",
            "Results update without page reload",
        ],
        hidden_tests=[
            HiddenTest("XSS in search input is sanitized", "security", "search=<script>", 10),
            HiddenTest("Special regex chars in search don't crash", "edge_case", "search=foo[bar]", 5),
            HiddenTest("Empty search shows all results", "edge_case", "search=", 3),
            HiddenTest("Search is case-insensitive", "usability", "search=PRODUCT", 4),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use existing frontend framework", "infrastructure", "hard"),
            ArchitectureConstraint("No server-side changes allowed (frontend only)", "scope", "medium"),
            ArchitectureConstraint("Must work on mobile viewport", "responsive", "medium"),
        ],
        difficulty=TicketDifficulty.MEDIUM,
        difficulty_score=0.60,
        estimated_revenue=350.0,
        estimated_hours=6.0,
        client_context="E-commerce startup with 5-person team. Vue.js frontend, existing inventory page. Budget $350.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use the existing Vue component pattern", "Check filters.js for existing filter logic"],
        tags=["frontend", "search", "filter", "dashboard"],
    ),
    ClientTicket(
        id="ticket-003",
        title="Fix flaky integration test suite",
        description="The client's CI pipeline has 3 flaky tests that fail 30% of the time. "
                    "'They're intermittent, probably race conditions. Just make them pass consistently.' "
                    "No one knows what causes the flakiness. The tests involve async operations.",
        ambiguous_elements=[
            "Root cause of flakiness not identified",
            "Whether to fix the tests or the underlying code",
            "Acceptable flakiness rate after fix not defined",
            "Whether to add retry logic or fix timing",
            "Test timeout values not specified",
        ],
        acceptance_criteria=[
            "All 3 tests pass consistently (>95% of runs)",
            "No test retry logic added (fix root cause)",
            "CI pipeline runs in under 10 minutes",
            "Existing test coverage is maintained",
        ],
        hidden_tests=[
            HiddenTest("Fix doesn't use time.sleep() as workaround", "quality", "grep time.sleep tests/", 10),
            HiddenTest("Other async tests still pass after fix", "regression", "full test suite", 5),
        ],
        architecture_constraints=[
            ArchitectureConstraint("No changes to test framework configuration", "infrastructure", "hard"),
            ArchitectureConstraint("Must not reduce test coverage", "quality", "hard"),
        ],
        difficulty=TicketDifficulty.HARD,
        difficulty_score=0.75,
        estimated_revenue=500.0,
        estimated_hours=8.0,
        client_context="Series A startup. Python backend with pytest. Flaky CI blocking deployments.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Look for shared mutable state between tests", "Check test teardown for cleanup issues"],
        tags=["testing", "flaky", "ci", "async"],
    ),
    ClientTicket(
        id="ticket-004",
        title="Add rate limiting to public API endpoints",
        description="The client has public API endpoints that are being abused. "
                    "'Add rate limiting. Use something standard like token bucket or sliding window.' "
                    "No rate limits specified. No mention of which endpoints need protection.",
        ambiguous_elements=[
            "Rate limit values (RPM/RPS) not specified",
            "Which endpoints to rate limit not specified",
            "Token bucket vs sliding window vs fixed window not decided",
            "What happens when limit exceeded (429 vs drop) not specified",
            "Whether rate limits apply per-IP or per-API-key",
        ],
        acceptance_criteria=[
            "Public GET endpoints are rate limited",
            "Rate limit exceeded returns 429 with Retry-After header",
            "Rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset) included in response",
            "Rate limiting works per-IP as default",
            "Configuration is in a single config file",
        ],
        hidden_tests=[
            HiddenTest("Rate limit resets correctly after window expires", "correctness", "wait+retry", 8),
            HiddenTest("Rate limit doesn't affect internal/health endpoints", "scope", "/health", 4),
            HiddenTest("Concurrent requests don't bypass limits", "race_condition", "parallel requests", 10),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use in-memory storage (no Redis dependency)", "infrastructure", "hard"),
            ArchitectureConstraint("Must not add more than 5ms latency", "performance", "hard"),
            ArchitectureConstraint("Must be thread-safe", "reliability", "medium"),
        ],
        difficulty=TicketDifficulty.HARD,
        difficulty_score=0.80,
        estimated_revenue=800.0,
        estimated_hours=10.0,
        client_context="B2B SaaS company. Django REST framework. 10 endpoints. Abused by competitors scraping data.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use time-window based approach for simplicity", "Store in dict with IP as key"],
        tags=["api", "rate-limiting", "security"],
    ),
    ClientTicket(
        id="ticket-005",
        title="Add data export feature (CSV/Excel)",
        description="The client wants to add a 'Download as CSV' and 'Download as Excel' button "
                    "to their analytics dashboard. 'The data is already in a table, just export it.' "
                    "No specification of what columns to include, date ranges, or formatting.",
        ambiguous_elements=[
            "Which columns to export vs display not specified",
            "Date format in export not specified",
            "Whether to include all data or filtered data only",
            "Maximum export size not specified",
            "Whether to stream large exports or generate synchronously",
        ],
        acceptance_criteria=[
            "CSV export button exports current view data",
            "Excel export button exports with .xlsx format",
            "Exports respect current filters",
            "Exports include column headers",
            "Large datasets (>10k rows) are handled without timeout",
        ],
        hidden_tests=[
            HiddenTest("Exported CSV handles commas in data correctly", "formatting", "data with commas", 5),
            HiddenTest("Excel export has correct column widths", "usability", "check column widths", 3),
            HiddenTest("Unicode characters in data export correctly", "encoding", "unicode data", 4),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use server-side generation, not client-side", "architecture", "hard"),
            ArchitectureConstraint("Must work with existing authentication", "security", "medium"),
        ],
        difficulty=TicketDifficulty.MEDIUM,
        difficulty_score=0.50,
        estimated_revenue=400.0,
        estimated_hours=6.0,
        client_context="Analytics startup. Python/FastAPI backend with React frontend. Users requesting export feature.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use csv module from stdlib", "Use openpyxl for Excel export"],
        tags=["export", "csv", "excel", "analytics"],
    ),
    ClientTicket(
        id="ticket-006",
        title="Add webhook system for events",
        description="The client needs a webhook system that notifies external services when certain events occur. "
                    "'Just let users configure URLs and we POST to them when things happen. Like Stripe webhooks.' "
                    "No details on retry policy, signing, delivery guarantees, or event format.",
        ambiguous_elements=[
            "Event payload format not specified",
            "Retry policy (count, backoff) not specified",
            "Whether to sign webhook payloads or not",
            "Delivery guarantees (at-least-once vs at-most-once) not specified",
            "Whether webhook endpoints are validated on configuration",
        ],
        acceptance_criteria=[
            "Webhook configuration UI (add/edit/delete endpoints)",
            "Webhook events are sent as POST with JSON body",
            "Failed deliveries retry 3 times with exponential backoff",
            "Webhook delivery logs are visible",
            "Webhook secrets are stored securely",
        ],
        hidden_tests=[
            HiddenTest("Webhook secret is never exposed in logs", "security", "check log output", 10),
            HiddenTest("Webhook timeout > 5s is treated as failure", "reliability", "slow endpoint", 5),
            HiddenTest("Concurrent webhook deliveries don't block each other", "concurrency", "parallel delivery", 7),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use existing database (no new DB)", "infrastructure", "hard"),
            ArchitectureConstraint("Must not use external message queue", "dependency", "hard"),
            ArchitectureConstraint("Webhook delivery must be async (non-blocking)", "performance", "hard"),
        ],
        difficulty=TicketDifficulty.EXPERT,
        difficulty_score=0.85,
        estimated_revenue=1200.0,
        estimated_hours=16.0,
        client_context="Growing SaaS platform. Existing event system but no external notifications. Want Stripe-quality webhooks.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use threading or asyncio for async delivery", "Store pending deliveries in DB table with status"],
        tags=["webhooks", "events", "integration", "async"],
    ),
    ClientTicket(
        id="ticket-007",
        title="Fix slow database queries on dashboard",
        description="The client's main dashboard loads in 12 seconds. 'The queries are slow, make them faster.' "
                    "No specific query identified. No performance budget defined. No mention of caching. "
                    "The tech lead mentions 'maybe add an index or two' without knowing which columns.",
        ambiguous_elements=[
            "Root cause of slow queries not identified",
            "Target load time not specified",
            "Whether to add caching or optimize queries not decided",
            "Which specific queries are slow not known",
            "Whether schema changes are allowed not specified",
        ],
        acceptance_criteria=[
            "Dashboard loads in under 2 seconds",
            "No schema changes to existing tables",
            "All existing functionality is preserved",
            "Solution is documented",
        ],
        hidden_tests=[
            HiddenTest("Solution uses database indexes not application caching", "strategy", "check approach", 6),
            HiddenTest("No N+1 query pattern introduced", "quality", "query count check", 8),
            HiddenTest("Solution works with existing data volume", "scale", "load test", 5),
        ],
        architecture_constraints=[
            ArchitectureConstraint("No new infrastructure (no Redis, no CDN)", "infrastructure", "hard"),
            ArchitectureConstraint("Must use existing ORM/query patterns", "style", "medium"),
            ArchitectureConstraint("Zero downtime deployment required", "operations", "hard"),
        ],
        difficulty=TicketDifficulty.HARD,
        difficulty_score=0.70,
        estimated_revenue=600.0,
        estimated_hours=8.0,
        client_context="Post-Series A startup. Django/PostgreSQL. Dashboard queries joining 6 tables. Growing data causing slowdowns.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Run EXPLAIN ANALYZE on the slow queries", "Look for missing composite indexes", "Consider select_related/prefetch_related"],
        tags=["database", "performance", "optimization"],
    ),
    ClientTicket(
        id="ticket-008",
        title="Add team/user permissions system",
        description="The client needs a permission system for their multi-tenant app. "
                    "'We need admins, editors, and viewers. Admins can do everything. Editors can edit content. "
                    "Viewers can only see things. Oh and some users should be super-admins.' "
                    "No details on permission inheritance, object-level permissions, or team scoping.",
        ambiguous_elements=[
            "Whether permissions are per-team or global not specified",
            "Object-level vs model-level permissions not decided",
            "Super-admin scope (all teams or specific teams) not defined",
            "Whether permissions are role-based or user-based not specified",
            "How to handle existing users without permissions not specified",
        ],
        acceptance_criteria=[
            "Three roles: admin, editor, viewer",
            "Super-admin role with cross-team access",
            "Permissions are per-team (not global)",
            "Admin can manage team members",
            "API endpoints check permissions before returning data",
        ],
        hidden_tests=[
            HiddenTest("Viewer cannot access admin-only endpoints", "authorization", "viewer+admin endpoint", 8),
            HiddenTest("Removing user from team revokes permissions immediately", "correctness", "remove+retry", 6),
            HiddenTest("Super-admin across all teams can access any team's data", "scope", "cross-team access", 7),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must work with existing User model", "infrastructure", "hard"),
            ArchitectureConstraint("No new auth provider/library", "dependency", "hard"),
            ArchitectureConstraint("Must support 10k+ teams", "scale", "hard"),
        ],
        difficulty=TicketDifficulty.EXPERT,
        difficulty_score=0.90,
        estimated_revenue=1500.0,
        estimated_hours=20.0,
        client_context="B2B SaaS. Existing single-tenant app being converted to multi-tenant. 50 existing customers to migrate.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use Django's built-in permission framework", "Create a Team-TeamMember-User model structure"],
        tags=["permissions", "auth", "multi-tenant", "rbac"],
    ),
    ClientTicket(
        id="ticket-009",
        title="Add error tracking and alerting",
        description="The client keeps finding out about production errors from their customers. "
                    "'Just catch errors and tell us somehow. Slack or email, whatever is easier.' "
                    "No error severity levels. No grouping logic. No alert thresholds.",
        ambiguous_elements=[
            "Error severity classification not defined",
            "Notification channel not decided (Slack vs email vs both)",
            "Alert frequency/throttling not specified",
            "Whether to include stack traces in notifications",
            "Error grouping logic (by message? by stack trace? by class?)",
        ],
        acceptance_criteria=[
            "Unhandled exceptions are caught and logged",
            "Errors are sent to Slack channel",
            "Errors are grouped by type to reduce noise",
            "Critical errors (500s) are alerted immediately",
            "Warning-level errors are batched hourly",
        ],
        hidden_tests=[
            HiddenTest("Sensitive data (passwords, tokens) is filtered from error reports", "security", "check error output", 10),
            HiddenTest("Error handler doesn't crash on malformed input", "resilience", "malformed error", 5),
            HiddenTest("Concurrent errors don't cause duplicate alerts", "race_condition", "rapid errors", 6),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use existing middleware/decorator patterns", "style", "medium"),
            ArchitectureConstraint("No external error tracking service (Sentry etc.)", "dependency", "hard"),
            ArchitectureConstraint("Must not block the request thread", "performance", "hard"),
        ],
        difficulty=TicketDifficulty.MEDIUM,
        difficulty_score=0.55,
        estimated_revenue=450.0,
        estimated_hours=6.0,
        client_context="Small team (4 devs) with growing SaaS. Using Slack for team communication. No error monitoring.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use middleware/WSGI middleware for Flask/Django", "Use Slack webhooks API for notifications"],
        tags=["monitoring", "error-tracking", "alerts", "slack"],
    ),
    ClientTicket(
        id="ticket-010",
        title="Add two-factor authentication (TOTP)",
        description="The client wants 2FA for their admin panel. 'Just add Google Authenticator support.' "
                    "No mention of backup codes. No mention of remember-device. No mention of setup flow.",
        ambiguous_elements=[
            "Whether to support authenticator apps only or SMS too",
            "Backup/recovery codes not mentioned",
            "Whether to allow 'remember this device for 30 days'",
            "2FA enforcement level (optional vs required for all) not specified",
            "Setup flow UX not designed",
        ],
        acceptance_criteria=[
            "Users can enable 2FA with Google Authenticator (TOTP)",
            "Login requires 6-digit code after password + 2FA enabled",
            "Setup page shows QR code and manual setup key",
            "Backup codes (8 x 8-digit) shown during setup",
            "Admin can disable 2FA for users who lose access",
        ],
        hidden_tests=[
            HiddenTest("Used TOTP code cannot be reused (window prevention)", "security", "reuse code", 10),
            HiddenTest("2FA setup requires current password confirmation", "security", "setup without password", 7),
            HiddenTest("Backup codes are one-time use only", "security", "reuse backup code", 6),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use TOTP (RFC 6238) not HOTP", "standard", "hard"),
            ArchitectureConstraint("All 2FA logic must be server-side", "security", "hard"),
            ArchitectureConstraint("Must not use external auth service", "dependency", "hard"),
        ],
        difficulty=TicketDifficulty.EXPERT,
        difficulty_score=0.85,
        estimated_revenue=1000.0,
        estimated_hours=14.0,
        client_context="Fintech startup. Handling customer financial data. Compliance requires 2FA for admin access.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use pyotp library for TOTP generation", "Store 2FA secret encrypted in DB", "Use qrcode library for QR generation"],
        tags=["security", "2fa", "authentication", "totp"],
    ),
    ClientTicket(
        id="ticket-011",
        title="Add bulk import from CSV",
        description="The client has a manual data entry process they want to automate. "
                    "'Just let users upload a CSV and it imports the data. Map columns automatically.' "
                    "No sample CSV provided. No column mapping rules. No validation requirements.",
        ambiguous_elements=[
            "Column name matching rules not specified (exact match vs fuzzy)",
            "Validation behavior (fail-fast vs collect all errors) not specified",
            "Duplicate handling (skip, update, error) not specified",
            "Maximum file size not specified",
            "Encoding assumptions not specified",
        ],
        acceptance_criteria=[
            "CSV upload with column auto-detection",
            "Preview shows first 5 rows before import",
            "Validation errors shown per-row with line numbers",
            "Valid rows import even when some rows have errors",
            "Import report shows: total, success, error counts",
        ],
        hidden_tests=[
            HiddenTest("BOM in UTF-8 CSV is handled correctly", "encoding", "BOM prefix", 4),
            HiddenTest("CSV with blank lines doesn't break import", "edge_case", "blank lines", 3),
            HiddenTest("Very long field values (>10k chars) are truncated not rejected", "robustness", "long field", 5),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must process large files (100MB+) without memory issues", "performance", "hard"),
            ArchitectureConstraint("Must be idempotent (re-importing same file is safe)", "reliability", "medium"),
        ],
        difficulty=TicketDifficulty.MEDIUM,
        difficulty_score=0.60,
        estimated_revenue=350.0,
        estimated_hours=5.0,
        client_context="Logistics company. Python/Django. Currently entering 500+ records/day manually. Want CSV import.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use csv.DictReader for auto-detection", "Process file in chunks with generator"],
        tags=["import", "csv", "data", "bulk"],
    ),
    ClientTicket(
        id="ticket-012",
        title="Add audit log for all data changes",
        description="The client is preparing for SOC2 audit and needs to track all data changes. "
                    "'Just log who changed what and when. Standard audit trail.' "
                    "No specification of which models to track, what data to capture, or retention policy.",
        ambiguous_elements=[
            "Which database tables/models to audit not specified",
            "What data to capture (old value, new value, both?) not specified",
            "Log retention period not specified",
            "Whether to capture read access (for sensitive data) not specified",
            "Audit log querying/filtering requirements not specified",
        ],
        acceptance_criteria=[
            "All CREATE/UPDATE/DELETE operations on main models are logged",
            "Audit log captures: actor, action, timestamp, old values, new values",
            "Audit logs are append-only (immutable)",
            "Admin UI for viewing audit logs with filters",
            "Audit logs are never deleted (10-year retention)",
        ],
        hidden_tests=[
            HiddenTest("Bulk operations each produce individual audit entries", "correctness", "bulk update", 6),
            HiddenTest("Audit log doesn't capture password fields", "security", "password in audit", 10),
            HiddenTest("System/service actions are logged with 'system' actor", "coverage", "non-user action", 4),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use database triggers or model signals (not middleware)", "architecture", "hard"),
            ArchitectureConstraint("Must not add >2ms to write operations", "performance", "hard"),
            ArchitectureConstraint("Audit table must be in separate database or schema", "infrastructure", "medium"),
        ],
        difficulty=TicketDifficulty.EXPERT,
        difficulty_score=0.88,
        estimated_revenue=1500.0,
        estimated_hours=18.0,
        client_context="Fintech preparing for SOC2 Type II audit. Django/PostgreSQL. Need audit trail for compliance.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use Django signals (post_save, post_delete)", "Create AuditLog model with GenericForeignKey"],
        tags=["audit", "compliance", "soc2", "logging"],
    ),
    ClientTicket(
        id="ticket-013",
        title="Add dark mode to web app",
        description="The client's users are requesting dark mode. 'Just add a toggle and make it dark. "
                    "Should take like an hour, right?' No design system. No color palette chosen. "
                    "No specification of which pages need dark mode support.",
        ambiguous_elements=[
            "Color palette for dark mode not defined",
            "Which components/pages to convert not specified",
            "Whether to use CSS variables or JS-based switching",
            "Persistence of user preference (localStorage vs server-side) not specified",
            "Whether to respect system prefers-color-scheme",
        ],
        acceptance_criteria=[
            "Dark mode toggle in navigation header",
            "All main pages render correctly in dark mode",
            "Toggle persists across page reloads",
            "Text contrast meets WCAG AA in dark mode",
            "Transitions between modes are smooth",
        ],
        hidden_tests=[
            HiddenTest("Custom scrollbars work in dark mode", "ui", "scrollbar colors", 3),
            HiddenTest("Third-party embedded content is not affected", "scope", "iframes/widgets", 4),
            HiddenTest("Print stylesheet is not affected by dark mode", "edge_case", "print preview", 3),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use CSS custom properties (variables)", "style", "medium"),
            ArchitectureConstraint("Must not require page reload on toggle", "ux", "hard"),
            ArchitectureConstraint("Must work in all modern browsers", "compatibility", "medium"),
        ],
        difficulty=TicketDifficulty.EASY,
        difficulty_score=0.35,
        estimated_revenue=200.0,
        estimated_hours=3.0,
        client_context="SaaS dashboard. React/CSS. Users mostly developers who want dark mode.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Define CSS custom properties on :root and [data-theme='dark']", "Use localStorage to persist preference"],
        tags=["ui", "dark-mode", "css", "frontend"],
    ),
    ClientTicket(
        id="ticket-014",
        title="Refactor monolithic view into components",
        description="The client's main dashboard view is 800+ lines of inline code. "
                    "'Just break it into smaller pieces. Use whatever pattern makes sense.' "
                    "No component boundaries defined. No test strategy for the refactored code.",
        ambiguous_elements=[
            "How to split the view into components not specified",
            "Component communication pattern (props vs store) not decided",
            "Whether to introduce a state management library",
            "Testing strategy for extracted components not specified",
            "Performance considerations (re-renders, memoization) not specified",
        ],
        acceptance_criteria=[
            "View is split into at least 5 components",
            "Each component has a single responsibility",
            "No functionality is lost in refactor",
            "Existing tests pass without modification",
            "New components are testable in isolation",
        ],
        hidden_tests=[
            HiddenTest("Component tree doesn't cause excessive re-renders", "performance", "render count check", 6),
            HiddenTest("Props are properly typed/validated", "quality", "proptypes/typescript", 4),
            HiddenTest("Extracted components handle loading/error states", "completeness", "all states", 5),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must follow existing project patterns", "style", "hard"),
            ArchitectureConstraint("No new dependencies allowed", "dependency", "hard"),
            ArchitectureConstraint("Must be done in 3 PRs maximum", "process", "medium"),
        ],
        difficulty=TicketDifficulty.MEDIUM,
        difficulty_score=0.50,
        estimated_revenue=300.0,
        estimated_hours=5.0,
        client_context="5-person dev team. React app. Dashboard view is unmaintainable. Tech debt cleanup sprint.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Identify logical sections of the view first", "Start with the most independent section"],
        tags=["refactor", "react", "components", "tech-debt"],
    ),
    ClientTicket(
        id="ticket-015",
        title="Add caching layer for API responses",
        description="The client's API is slow for frequently accessed data. "
                    "'Add caching. Use Redis or something. Make it fast.' "
                    "No cache invalidation strategy. No TTL values. No hit rate monitoring.",
        ambiguous_elements=[
            "Which endpoints to cache not specified",
            "Cache TTL values not specified",
            "Cache invalidation strategy not defined",
            "Whether to cache at HTTP level or application level",
            "Monitoring/observability of cache not specified",
        ],
        acceptance_criteria=[
            "GET /api/products response time < 100ms (was 800ms)",
            "Cache is invalidated when data changes",
            "Cache hit rate is >80%",
            "Cache gracefully degrades on Redis outage",
            "Cache statistics endpoint for monitoring",
        ],
        hidden_tests=[
            HiddenTest("Cache stampede prevention (dog-pile effect)", "reliability", "concurrent misses", 8),
            HiddenTest("Cache key includes relevant query parameters", "correctness", "different params", 5),
            HiddenTest("Stale cache never returns deleted data", "consistency", "delete+get", 6),
        ],
        architecture_constraints=[
            ArchitectureConstraint("Must use Redis (already deployed)", "infrastructure", "hard"),
            ArchitectureConstraint("Must support multi-tenancy (separate caches per tenant)", "multi-tenant", "hard"),
            ArchitectureConstraint("Cache layer must be hot-swappable", "architecture", "medium"),
        ],
        difficulty=TicketDifficulty.EXPERT,
        difficulty_score=0.82,
        estimated_revenue=900.0,
        estimated_hours=12.0,
        client_context="B2B SaaS. Django REST Framework. Redis already deployed for sessions. API latency affecting user retention.",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        hints=["Use Django's cache framework with Redis backend", "Use cache_page decorator or manual cache/get"],
        tags=["caching", "performance", "redis", "api"],
    ),
]


def get_seeded_ticket(ticket_id: str) -> ClientTicket:
    for t in SEEDED_TICKETS:
        if t.id == ticket_id:
            return t
    raise KeyError(f"Ticket '{ticket_id}' not found. Available: {[t.id for t in SEEDED_TICKETS]}")


def list_seeded_tickets(difficulty: TicketDifficulty = None) -> list[ClientTicket]:
    if difficulty:
        return [t for t in SEEDED_TICKETS if t.difficulty == difficulty]
    return SEEDED_TICKETS
