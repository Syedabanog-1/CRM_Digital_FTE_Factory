# TechCorp Suite — Product Documentation

## TaskFlow (Project Management)

TaskFlow is TechCorp's core project management module. It supports Agile, Scrum, and Waterfall methodologies with flexible views and powerful task tracking.

### Creating a Project
1. Click **"New Project"** from the dashboard or sidebar
2. Enter a project name and optional description
3. Select methodology: Kanban, Scrum, or Waterfall
4. Invite team members by email
5. Choose a template or start from scratch

### Kanban Boards
Drag-and-drop task cards between columns. Default columns: To Do, In Progress, In Review, Done. You can add custom columns via Board Settings > Columns. WIP (Work In Progress) limits can be set per column.

### Sprint Planning
Available in Scrum mode. Go to **Sprints > Plan Sprint**. Drag backlog items into the sprint. Set sprint duration (1-4 weeks). Track velocity across sprints in InsightHub.

### Task Management
- **Create a task**: Click "+" or press "N" in any board view
- **Assign**: Click the avatar icon and select a team member
- **Due dates**: Click the calendar icon; overdue tasks appear in red
- **Subtasks**: Open a task > Add Subtask; subtasks have their own assignees
- **Labels/Tags**: Create custom labels for categorization (e.g., "bug", "feature", "urgent")
- **Dependencies**: Link tasks with "blocks" or "blocked by" relationships

### Troubleshooting
- **Q: I can't create a new project** — Verify you have "Project Creator" or "Admin" role. Starter plans are limited to 10 active projects.
- **Q: Tasks aren't showing on my board** — Check your active filters. Click "Clear Filters" in the board toolbar.
- **Q: I can't assign a team member** — They must be invited to the project first. Go to Project Settings > Members.
- **Q: Sprint velocity seems wrong** — Velocity counts only completed story points. Ensure tasks have story point estimates.

---

## InsightHub (Analytics & Reporting)

InsightHub provides real-time analytics and customizable reports for project tracking and team performance.

### Dashboard Creation
1. Navigate to **InsightHub > Dashboards**
2. Click **"New Dashboard"**
3. Add widgets: burndown chart, velocity tracker, team utilization, task distribution
4. Arrange widgets by dragging them into position
5. Share the dashboard with your team via the Share button

### Report Types
- **Burndown Chart**: Shows remaining work vs. time in a sprint
- **Velocity Report**: Tracks story points completed per sprint over time
- **Team Utilization**: Percentage of capacity used per team member
- **Task Distribution**: Breakdown of tasks by status, assignee, or label
- **Custom KPIs**: Define your own metrics using the KPI builder

### Data Export
Go to **InsightHub > Export**. Choose format: CSV (raw data) or PDF (formatted report). Schedule automatic exports: daily, weekly, or monthly delivery to email.

### Troubleshooting
- **Q: My dashboard is showing old data** — Click the refresh icon or check if auto-refresh is enabled (Settings > Dashboard > Auto-refresh interval).
- **Q: I can't create custom KPIs** — Custom KPIs require Professional or Enterprise plan.
- **Q: Export is failing** — Large datasets may timeout. Try filtering to a smaller date range.
- **Q: Charts show "No Data"** — Ensure tasks have the required fields (story points, dates, assignees).

---

## ConnectBridge (Integrations)

ConnectBridge connects TechCorp with your existing tools through native integrations and webhook automation.

### Setting Up Slack Integration
1. Go to **Settings > Integrations > Slack**
2. Click **"Connect to Slack"**
3. Authorize TechCorp in the Slack OAuth popup
4. Select which Slack channels receive notifications
5. Configure notification types (task created, completed, commented)

### GitHub Integration
1. Go to **Settings > Integrations > GitHub**
2. Click **"Connect GitHub"** and authorize
3. Link GitHub repositories to TechCorp projects
4. Enable auto-linking: commits referencing task IDs (e.g., `TC-123`) automatically link
5. PR status updates appear as task comments

### Zapier Webhooks
1. Go to **Settings > Integrations > Webhooks**
2. Click **"Create Webhook"**
3. Copy the webhook URL
4. In Zapier, use "Webhooks by Zapier" as the trigger
5. Configure the Zap action (e.g., create task, update status)

### Troubleshooting
- **Q: My Slack integration stopped working** — Go to Settings > Integrations > Slack and click "Reconnect." Slack tokens expire if your workspace admin revokes app access.
- **Q: GitHub commits aren't linking** — Ensure commit messages include the task ID format `TC-XXXX`. The repository must be linked to the correct project.
- **Q: Webhook isn't firing** — Check the webhook logs at Settings > Integrations > Webhooks > Logs. Verify the endpoint URL is correct and accessible.
- **Q: Integration sync is delayed** — Real-time sync may experience up to 30-second delays during peak hours. Verify the integration status shows "Active."

---

## AlertStream (Notifications)

AlertStream manages all notification preferences across email, mobile, and in-app channels.

### Configuring Notifications
1. Go to **Settings > Notifications**
2. Choose notification types: task assignments, comments, @mentions, due date reminders, sprint updates
3. Set delivery channel per type: email, push, in-app, or any combination
4. Configure frequency: instant, hourly digest, daily digest, weekly summary

### Email Digests
- **Daily Digest**: Sent at your preferred time, summarizes all activity from the past 24 hours
- **Weekly Summary**: Sent Monday morning, includes project progress, upcoming deadlines, and team highlights
- Configure at: Settings > Notifications > Email Preferences

### Quiet Hours
Set time periods when no push notifications are sent. Go to Settings > Notifications > Quiet Hours. Set start and end times. Emergency notifications (critical mentions) can override quiet hours if enabled.

### Troubleshooting
- **Q: I'm not receiving email notifications** — Check your spam/junk folder. Verify your email address at Settings > Profile. Ensure notifications are enabled for your desired event types.
- **Q: Push notifications aren't working on mobile** — Ensure the TechCorp mobile app has notification permissions enabled in your device settings. Try logging out and back in.
- **Q: I'm getting too many notifications** — Switch to digest mode (daily or weekly) instead of instant notifications. You can also mute specific projects.
- **Q: @mention alerts aren't appearing** — Verify that @mention notifications are enabled at Settings > Notifications. The person mentioning you must use the exact format @username.

---

## DevPortal (API & Developer Tools)

DevPortal provides REST API access for building custom integrations, automations, and extending TechCorp functionality.

### Authentication
TechCorp API supports two authentication methods:
- **API Key**: Generate at Settings > API > API Keys. Include in header: `Authorization: Bearer YOUR_API_KEY`
- **OAuth2**: For third-party apps. Register your app at Settings > API > OAuth Apps. Supports authorization code flow.

### Rate Limits
| Plan | Requests/Minute | Daily Limit |
|------|-----------------|-------------|
| Starter | 1,000 | 50,000 |
| Professional | 5,000 | 250,000 |
| Enterprise | Unlimited | Unlimited |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Common API Endpoints
- `GET /api/v1/projects` — List all projects
- `POST /api/v1/projects/{id}/tasks` — Create a task
- `GET /api/v1/tasks/{id}` — Get task details
- `PUT /api/v1/tasks/{id}` — Update a task
- `GET /api/v1/users/me` — Current user info
- `POST /api/v1/webhooks` — Create a webhook subscription

### Webhook Setup
1. Go to **Settings > API > Webhooks**
2. Click **"Add Webhook"**
3. Enter your endpoint URL (must be HTTPS)
4. Select events to subscribe to (task.created, task.updated, comment.added, etc.)
5. Set a webhook secret for signature verification
6. Test the webhook with the "Send Test" button

### Troubleshooting
- **Q: I'm getting 429 Too Many Requests** — You've exceeded your rate limit. Check `X-RateLimit-Reset` header for when it resets. Consider upgrading your plan for higher limits.
- **Q: API key isn't working** — Verify the key is active at Settings > API > API Keys. Keys can be revoked by workspace admins. Ensure you're using the correct header format.
- **Q: Webhook signatures don't match** — Verify you're using the correct webhook secret. Compute HMAC-SHA256 of the raw request body using your secret.
- **Q: OAuth token expired** — Use the refresh token to obtain a new access token. Refresh tokens are valid for 30 days.

---

## TeamSync (Collaboration)

TeamSync enables real-time collaboration with comments, file sharing, and team communication within TechCorp projects.

### Comments and @Mentions
- Add comments on any task by clicking the comment icon
- Use `@username` to mention and notify team members
- Comments support markdown formatting (bold, italic, code blocks, links)
- Thread replies keep discussions organized — click "Reply" on any comment

### File Sharing
- Drag and drop files onto a task or use the attachment button
- Maximum file size: 100MB per file
- Supported formats: images, PDFs, documents, spreadsheets, ZIP archives
- Version history: upload a new version of a file and previous versions are preserved

### Guest Access
- Invite external collaborators: Project Settings > Members > Invite Guest
- Guests can view and comment on tasks they're invited to
- Guests cannot create projects or access billing
- Guest access is available on Professional and Enterprise plans

### Troubleshooting
- **Q: I can't upload files** — Check that the file is under 100MB. Verify your storage quota isn't full (check at Settings > Storage).
- **Q: @mentions aren't notifying people** — The person must be a member of the project. Verify the exact username format. Check their notification settings.
- **Q: Guest can't access the project** — Guests need an explicit invitation to each project. Resend the invitation from Project Settings > Members.
- **Q: Comments are disappearing** — This may be a display issue. Refresh the page. If persistent, clear browser cache. Deleted comments show "[deleted]" placeholder.

---

## Account Management

### Password Reset
1. Go to the login page and click **"Forgot Password?"**
2. Enter your registered email address
3. Check your inbox for the reset link (valid for 1 hour)
4. Click the link and set a new password
5. Password requirements: minimum 8 characters, at least one uppercase letter, one number, and one special character

### Two-Factor Authentication (2FA)
1. Go to **Settings > Security > Two-Factor Authentication**
2. Click **"Enable 2FA"**
3. Scan the QR code with an authenticator app (Google Authenticator, Authy, etc.)
4. Enter the verification code to confirm
5. Save your backup recovery codes in a secure location

### Team Member Management
- **Add members**: Settings > Team > Invite Members. Enter email addresses.
- **Roles**: Owner (full access), Admin (manage settings, no billing), Member (project access), Guest (limited access)
- **Remove members**: Settings > Team > click member > Remove from workspace
- **Transfer ownership**: Settings > Team > click member > Transfer Ownership

### Billing Management
- View current plan: **Settings > Billing > Current Plan**
- Upgrade/downgrade: **Settings > Billing > Change Plan**
- Payment methods: Credit card, debit card. Enterprise plans support invoicing.
- Billing cycle: Monthly or annual (annual saves 20%)
- View invoices: **Settings > Billing > Invoices**

### SSO Configuration (Enterprise Only)
1. Go to **Settings > Security > SSO**
2. Select your identity provider (Okta, Azure AD, Google Workspace, OneLogin)
3. Enter your SSO metadata URL or upload the XML configuration
4. Configure attribute mapping (email, name, department)
5. Enable "Enforce SSO" to require SSO for all users

### Troubleshooting
- **Q: I can't log in** — Try "Forgot Password?" to reset. If SSO is enabled, use your company's SSO login page. Clear browser cookies if you see a redirect loop.
- **Q: 2FA code isn't working** — Ensure your device clock is synchronized (time-based codes are sensitive to clock drift). Use a backup recovery code if needed.
- **Q: I can't add more team members** — Check your plan's user limit. Starter plans support up to 25 users. Upgrade to Professional for up to 100.
- **Q: How do I export my data?** — Go to Settings > Account > Export Data. Choose full export (all projects, tasks, comments, files) or selective export. Export is delivered as a ZIP file to your email within 24 hours.
