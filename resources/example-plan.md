# Example Plan: Multi-Phase Feature with Parallel Tasks

This example demonstrates a phased plan where Phase 2 uses parallel workers.

---

## Phase 1: Database Schema

### 1.1 Create migration
- Add migration file for `projects` table (id, name, description, owner_id, created_at, updated_at)
- Add migration file for `tasks` table (id, project_id, title, status, assignee_id, due_date, created_at)

### 1.2 Create models
- `src/models/project.ts` — Sequelize model with associations
- `src/models/task.ts` — Sequelize model with associations

### 1.3 Seed data
- Create seed file with 3 sample projects and 10 sample tasks

**Verification:** `npm run migrate && npm run seed && npm test`

---

## Phase 2: API Endpoints (Parallel Workers)

### Worker A: Projects API
- `GET /api/projects` — list with pagination
- `POST /api/projects` — create with validation
- `GET /api/projects/:id` — get by ID with tasks
- `PUT /api/projects/:id` — update
- `DELETE /api/projects/:id` — soft delete

### Worker B: Tasks API
- `GET /api/tasks` — list with filters (project, status, assignee)
- `POST /api/tasks` — create with validation
- `PUT /api/tasks/:id` — update status/assignee
- `DELETE /api/tasks/:id` — soft delete

### Worker C: Search & Filtering
- `GET /api/search?q=...` — full-text search across projects and tasks
- Query parameter filtering for both endpoints
- Sorting by any field

**Verification:** Each worker runs `npm test` in its worktree. Coordinator runs full suite after integration.

---

## Phase 3: Frontend

### 3.1 Project list page
- Fetch and display projects with pagination
- Create project modal
- Delete project confirmation

### 3.2 Task board
- Kanban-style board grouped by status
- Drag-and-drop status changes
- Filter by project, assignee, due date

### 3.3 Search bar
- Global search component
- Display results grouped by type
- Debounced input with loading state

**Verification:** `npm test && npm run build`
