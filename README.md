This project is a text-based game engine built around AI-driven narrative and deterministic validation. The game is structured as a series of conceptual levels where progression is not achieved by executing specific commands, but by demonstrating understanding. Player input is interpreted semantically, evaluated against the current level’s intent, and transformed into state changes that are then strictly validated by deterministic rules.

The core engine runs in a fixed loop: player input → intent gate (LLM) → game state patch → deterministic validator/modifier → win/loss check → outcome narration (LLM). LLMs are used only for interpretation and narration; all authoritative state transitions, validation, timers, and resets are deterministic. This separation is critical to prevent narrative drift and to keep gameplay predictable, testable, and replayable.

Each level defines its own unlock condition, narrative framing, and failure mode. Advancement requires the player to sufficiently convince the intent gate that they understand what the level requires, not merely that they used the correct words. Levels operate under a deterministic turn-based clock (e.g. a fixed number of player inputs). As the clock advances, narration escalates in urgency or explicitness. When the clock expires, the level resets and narrative memory is cleared, with the narrator explicitly signaling that the player did not yet grasp the requirement.

Failure is treated as feedback, not punishment. Resets are intentional, legible events that reinforce the game’s core theme: understanding over execution. The system is designed to explore the boundary between player intent, AI interpretation, and hard game rules, while remaining fully text-based and mechanically transparent to the engine.
## Quick Start with Docker

The easiest way to run the escape-room game is using Docker Compose, which automatically sets up both the Ollama LLM service and the game application.

### Prerequisites
- Docker and Docker Compose installed

### Running the Game

```bash
# Build and start all services (Ollama + game)
docker-compose up --build

# The game will automatically:
# 1. Start Ollama service
# 2. Pull the llama3.1:8b model (first run only, ~4-6GB)
# 3. Launch the game and wait for input
```

The first run will take several minutes to download the llama3.1:8b model. Subsequent runs will be much faster.

### Game Commands

Once the game starts, you can:
- Type commands to interact with the current level
- Type `quit` to exit the game
- The game runs between-floors.yaml level by default

### Advanced Docker Usage

**Run a different level:**
```bash
docker-compose run game python game/loop.py --evaluator-type llm --narrator-type llm --level bobs-plan.yaml
```

**Run the game without rebuilding:**
```bash
docker-compose up
```

**Stop the services:**
```bash
docker-compose down
```

**Keep Ollama service running, restart just the game:**
```bash
docker-compose up game
```

### Configuration

- **Model configuration:** Edit `config/models.dev.yaml` to change the LLM model or temperature settings
- **Levels:** Add new YAML level files to the `levels/` directory
- **Environment:** The docker-compose.yml sets `OLLAMA_BASE_URL=http://ollama:11434` for service communication

### Docker Architecture

- **Ollama Service**: Runs the LLM server with automatic model pulling
- **Game Service**: Python application that connects to Ollama
- **Shared Network**: Services communicate via a Docker network bridge
- **Persistent Storage**: Ollama models are stored in a named volume to avoid re-downloading