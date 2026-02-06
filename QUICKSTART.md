# 🚀 Quick Start Guide - Escape Room with Docker

## TL;DR - Get Running in 2 Commands

```bash
# 1. Build and run (includes everything - Ollama + models + game)
docker-compose up --build

# 2. Play the game!
```

That's it! First run will download and cache ~4-6GB of the llama3.1:8b model (takes 5-15 min on typical internet). **Subsequent runs start instantly** because the model is cached.

---

## What's Inside?

Everything you need is **in a single Docker container**:
- ✅ Ollama LLM service (runs inside container)
- ✅ llama3.1:8b model (auto-downloaded first run, then cached)
- ✅ Escape Room game app
- ✅ All dependencies pre-installed

No external services to manage!

---

## Useful Commands

```bash
# Start the game
docker-compose up --build

# Run a different level
docker-compose run game python game/loop.py --evaluator-type llm --narrator-type llm --level bobs-plan.yaml

# Run tests
docker-compose run game pytest tests/

# Clean up (delete model cache)
docker-compose down -v

# View logs (if running in background)
docker-compose logs -f
```

---

## Levels Available

- `between-floors.yaml` (default)
- `bobs-plan.yaml`
- `test-evaluator.yaml`

---

## Troubleshooting

**"First run is taking forever"?**
- Normal! llama3.1:8b is ~4-6GB. Check progress in the logs.

**"Out of disk space"?**
- The model is large. Free up 8GB+ or run `docker-compose down -v` to delete volumes.

**"Port conflicts"?**
- The container doesn't expose external ports by default. If you need to access Ollama from outside, edit `docker-compose.yml` and add under the `game` service:
  ```yaml
  ports:
    - "11434:11434"
  ```

**"Want to edit code and see changes instantly"?**
- Use `docker-compose -f docker-compose.dev.yml up` (mounts code volume)

---

## Project Architecture

```
escape-room/
├── Dockerfile           # Self-contained image with Ollama + game
├── docker-compose.yml   # Simple single-service setup
├── docker-compose.dev.yml  # Dev setup with live code mounts
├── config/
│   └── models.dev.yaml  # LLM settings
├── llm/                 # LLM integration
├── game/                # Game loop & logic
├── engine/              # Core game engine
└── levels/              # Level definitions (YAML)
```

---

Enjoy! 🎮
