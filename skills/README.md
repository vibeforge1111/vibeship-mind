# Spawner Skills

Local skill packs for Claude Code. Zero cost, works offline.

## Quick Start

Skills are auto-installed when you first use Spawner. No manual setup needed.

**If you need to manually install/update:**

```bash
# Clone to your home directory
git clone https://github.com/vibeforge1111/vibeship-spawner-skills ~/.spawner/skills

# Update skills
cd ~/.spawner/skills && git pull
```

## How It Works

1. You chat with Claude using Spawner
2. Claude reads skills directly from `~/.spawner/skills/`
3. No API calls for skill loading = free, fast, offline

## Skill Packs

| Pack | Skills | Description |
|------|--------|-------------|
| `essentials` | ~30 | Core skills for building apps (auto-installed) |
| `data` | 6 | Database and data engineering |
| `ai` | 3 | LLM, ML, and AI systems |
| `startup` | 8+ | Founder and fundraising skills |
| `marketing` | 10+ | Growth, content, SEO |
| `frameworks` | 15+ | React, Next.js, Vue, etc. |

## Directory Structure

```
~/.spawner/skills/
├── registry.yaml          # Pack definitions
├── development/           # Backend, frontend, devops, etc.
├── data/                  # Databases, vectors, graphs
├── ai/                    # LLM, ML, embeddings
├── design/                # UI, UX, branding
├── frameworks/            # React, Next.js, Vue, etc.
├── marketing/             # Growth, content, SEO
├── startup/               # YC, fundraising, founder
├── strategy/              # Business, market analysis
├── communications/        # Writing, pitching
├── integration/           # APIs, webhooks
└── product/               # PM, roadmapping
```

## Skill Format

Each skill has 4 YAML files:

```
backend/
├── skill.yaml           # Identity, patterns, anti-patterns
├── sharp-edges.yaml     # Gotchas and warnings
├── validations.yaml     # Code checks
└── collaboration.yaml   # Handoffs and prerequisites
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add or improve skills.

## License

MIT
