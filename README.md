# Tournament SaaS

A multi-tenant SaaS platform for hosting and managing esports tournaments. Built with Django, PostgreSQL, and deployed on Railway.

## Features

- **Multi-org support** — each organization manages its own tournaments, teams, and registrations independently
- **Subscription plans** — tournament creation is gated by plan limits (billing module)
- **Single-elimination brackets** — industry-standard power-of-2 bye system (same algorithm used by Challonge and Battlefy)
- **Match result reporting** — winner advances automatically to the next match; champion is set when the final match completes
- **Team registration flow** — teams register and await approval before being seeded into the bracket
- **Bulk approve** — approve multiple registrations at once before bracket generation

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.x |
| Database | PostgreSQL |
| Auth | Django built-in auth |
| Deployment | Railway |
| Frontend | Django Templates |

## Project Structure

```
tournament-saas/
├── accounts/          # User authentication and profiles
├── billing/           # Subscription plans and limits
├── config/            # Django settings
├── core/              # Shared utilities
├── matches/           # Match result tracking
├── organizations/     # Org management
├── registrations/     # Team registration and approval
├── tournaments/       # Tournament creation, bracket generation, match reporting
└── templates/         # HTML templates
```

## Bracket Algorithm

Uses the power-of-2 bye system:

1. `bracket_size` = next power of 2 ≥ number of teams
2. Top seeds (earliest registered) receive byes and skip Round 1
3. Round 1 is played by remaining teams (always an even count)
4. Winners advance via `next_match` FK pointers wired at bracket generation time

Example with 5 teams (bracket_size=8, 3 byes):
```
Round 1: Seed4 vs Seed5
Round 2: Seed1 vs Seed2 | Seed3 vs Winner(R1)
Round 3: Winner vs Winner  ← Final
```

## Local Development

```bash
# Clone and set up
git clone https://github.com/Anant-spec/tournament-saas.git
cd tournament-saas
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Running Tests

```bash
python manage.py test
```

## Live Demo

[https://tournament-status.up.railway.app](https://tournament-status.up.railway.app)
